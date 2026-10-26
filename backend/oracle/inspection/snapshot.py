"""Controlled snapshot ingestion for local directories and remote Git repositories."""

import os
import re
import shutil
import subprocess
import tempfile
from typing import List, Optional
from urllib.parse import urlparse

from oracle.core.config import settings
from oracle.inspection.policy import (
    PathTraversalError,
    SnapshotTimeoutError,
    InspectionPolicyError,
    redact_secrets,
)

# Supported schemes for remote or local Git acquisition
SUPPORTED_GIT_SCHEMES = {"http", "https", "git", "ssh", "file"}


class SnapshotContext:
    """Encapsulates an acquired repository snapshot on the local filesystem."""

    def __init__(
        self,
        root_path: str,
        source_type: str,
        target_location: str,
        commit_hash: Optional[str] = None,
        temp_dir: Optional[str] = None,
    ) -> None:
        self.root_path = root_path
        self.source_type = source_type
        self.target_location = target_location
        self.commit_hash = commit_hash
        self._temp_dir = temp_dir

    def cleanup(self) -> None:
        """Remove temporary snapshot directory if one was created."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except OSError:
                pass
            self._temp_dir = None

    def __enter__(self) -> "SnapshotContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


def resolve_permitted_roots(configured_roots: Optional[List[str]] = None) -> List[str]:
    """Resolve and normalize permitted directory roots for local repository ingestion."""
    raw_roots = configured_roots if configured_roots else settings.permitted_local_roots

    if not raw_roots:
        # Default safely to the current working directory and system temp directory
        raw_roots = [os.getcwd(), tempfile.gettempdir()]

    normalized: List[str] = []
    for r in raw_roots:
        if r and os.path.exists(r):
            normalized.append(os.path.abspath(os.path.realpath(r)))
    return normalized


def ingest_local_directory(
    local_path: str,
    permitted_roots: Optional[List[str]] = None,
) -> SnapshotContext:
    """Safely validate and acquire a read-only snapshot context for a local directory.

    Enforces strict path containment, rejects directory traversal (../),
    and prevents symlink escapes outside the permitted root boundary.
    """
    if not local_path or not local_path.strip():
        raise InspectionPolicyError("Local directory path cannot be empty.")

    clean_path = local_path.strip()
    if clean_path.startswith("file://"):
        clean_path = clean_path[len("file://") :]
        if clean_path.startswith("/") and os.name == "nt" and len(clean_path) > 2 and clean_path[2] == ":":
            clean_path = clean_path[1:]

    # Strip URL query parameters and fragments from local directory paths
    if "?" in clean_path:
        clean_path = clean_path.split("?", 1)[0]
    if "#" in clean_path:
        clean_path = clean_path.split("#", 1)[0]

    # Resolve real path, canonicalizing all symlinks and traversal dots
    real_target = os.path.abspath(os.path.realpath(clean_path))

    if not os.path.exists(real_target):
        raise FileNotFoundError(f"Local repository path does not exist: {local_path}")

    if not os.path.isdir(real_target):
        raise InspectionPolicyError(f"Local repository path must be a directory: {local_path}")

    # Enforce path containment
    roots = resolve_permitted_roots(permitted_roots)
    is_contained = False
    for root in roots:
        try:
            common = os.path.commonpath([root, real_target])
            if common == root:
                is_contained = True
                break
        except ValueError:
            # Different drives on Windows (e.g. C: vs D:)
            continue

    if not is_contained:
        raise PathTraversalError(
            f"Path traversal violation: Target '{local_path}' is outside permitted directory roots."
        )

    # Attempt to read commit hash if local directory happens to be a git repository
    commit_hash = None
    git_dir = os.path.join(real_target, ".git")
    if os.path.isdir(git_dir):
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=real_target,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                commit_hash = res.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            pass

    return SnapshotContext(
        root_path=real_target,
        source_type="local_directory",
        target_location=local_path,
        commit_hash=commit_hash,
        temp_dir=None,
    )


def ingest_git_repository(
    git_url: str,
    timeout_seconds: Optional[float] = None,
) -> SnapshotContext:
    """Clone a bounded shallow snapshot of a remote Git repository into an isolated temporary directory.

    Enforces:
    - Scheme validation (http, https, git, ssh, file)
    - Rejection of embedded credentials in URL
    - Bounded shallow clone (--depth 1, --no-tags, --no-recurse-submodules)
    - Disabled hooks (-c core.hooksPath=/dev/null)
    - Subprocess argument list (NEVER shell string interpolation)
    - Disabled interactive prompts (GIT_TERMINAL_PROMPT=0)
    - Strict timeout enforcement
    """
    if not git_url or not git_url.strip():
        raise InspectionPolicyError("Git URL cannot be empty.")

    clean_url = git_url.strip()
    timeout = timeout_seconds if timeout_seconds is not None else float(settings.inspection_timeout_seconds)

    # Validate scheme
    parsed = urlparse(clean_url)
    scheme = parsed.scheme.lower() if parsed.scheme else ""

    if scheme not in SUPPORTED_GIT_SCHEMES and not clean_url.startswith("git@"):
        raise InspectionPolicyError(
            f"Unsupported repository scheme '{scheme}'. Supported schemes: {', '.join(sorted(SUPPORTED_GIT_SCHEMES))}"
        )

    # Reject embedded credentials in URL to prevent leaking tokens or passwords
    if "@" in parsed.netloc and ":" in parsed.netloc.split("@")[0]:
        raise InspectionPolicyError(
            "Repository URL must not contain embedded user credentials. Pass credentials via secure configuration."
        )

    temp_dir = tempfile.mkdtemp(prefix="oracle_git_snapshot_")
    sanitized_url = redact_secrets(clean_url)

    # Null hooks path to prevent arbitrary hook execution from cloned repositories
    hooks_path = "NUL" if os.name == "nt" else "/dev/null"

    clone_cmd = [
        "git",
        "clone",
        "--depth",
        "1",
        "--no-tags",
        "--no-recurse-submodules",
        "-c",
        f"core.hooksPath={hooks_path}",
        clean_url,
        temp_dir,
    ]

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = ""

    try:
        proc = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )

        if proc.returncode != 0:
            shutil.rmtree(temp_dir, ignore_errors=True)
            err_msg = redact_secrets(proc.stderr.strip() or proc.stdout.strip())
            raise InspectionPolicyError(f"Git clone failed (exit code {proc.returncode}): {err_msg}")

        # Capture commit SHA of the shallow snapshot
        commit_hash = None
        rev_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        if rev_proc.returncode == 0:
            commit_hash = rev_proc.stdout.strip()

        return SnapshotContext(
            root_path=temp_dir,
            source_type="git",
            target_location=sanitized_url,
            commit_hash=commit_hash,
            temp_dir=temp_dir,
        )

    except subprocess.TimeoutExpired:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise SnapshotTimeoutError(
            f"Git snapshot acquisition timed out after {timeout} seconds for {sanitized_url}"
        )
    except FileNotFoundError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise InspectionPolicyError("Git executable was not found on system PATH.")
