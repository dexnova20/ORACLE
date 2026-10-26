"""Security, exclusion, secret redaction, and resource policies for repository inspection."""

import os
import re
import time
from typing import Set

# Excluded directory names (never traversed during repository inspection)
EXCLUDED_DIRECTORIES: Set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "dist",
    "build",
    "target",
    "bin",
    "obj",
    ".idea",
    ".vscode",
    ".cargo",
}

# Binary and non-source extensions skipped from code parsing
BINARY_EXTENSIONS: Set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".o",
    ".a",
    ".class",
    ".jar",
    ".war",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".mp4",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
}

# Secret patterns for diagnostic metadata and error message redaction
SECRET_PATTERNS = [
    re.compile(r"://([^:/]+):([^@]+)@", re.IGNORECASE),  # URL credentials: ://user:pass@
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b"),  # GitHub tokens
    re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}\b"),  # GitLab tokens
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access keys
    re.compile(r"(?i)\b(password|secret|token|api_key|apikey|private_key)\b\s*[:=]\s*['\"]?([^'\"\s]{6,})['\"]?"),
]


class InspectionPolicyError(Exception):
    """Raised when repository content or dimensions violate safety policies."""

    pass


class ResourceLimitExceededError(InspectionPolicyError):
    """Raised when file count, file size, or byte total exceeds safety bounds."""

    pass


class SnapshotTimeoutError(InspectionPolicyError):
    """Raised when an ingestion or inspection operation exceeds its time quota."""

    pass


class PathTraversalError(InspectionPolicyError):
    """Raised when a local path escapes its permitted boundary."""

    pass


def redact_secrets(text: str) -> str:
    """Sanitize strings by redacting embedded passwords, tokens, and secret keys."""
    if not text:
        return text

    sanitized = text

    # Redact URL credentials ://user:pass@ -> ://[REDACTED]:[REDACTED]@
    sanitized = re.sub(r"://([^:/]+):([^@]+)@", r"://[REDACTED]:[REDACTED]@", sanitized)

    # Redact key/value secrets
    def _kv_replace(match: re.Match) -> str:
        key = match.group(1)
        return f"{key}=[REDACTED]"

    sanitized = re.sub(
        r"(?i)\b(password|secret|token|api_key|apikey|private_key)\b\s*[:=]\s*['\"]?([^'\"\s]{6,})['\"]?",
        _kv_replace,
        sanitized,
    )

    # Redact well-known vendor token prefixes
    sanitized = re.sub(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b", "[REDACTED_GITHUB_TOKEN]", sanitized)
    sanitized = re.sub(r"\bglpat-[A-Za-z0-9_\-]{20,}\b", "[REDACTED_GITLAB_TOKEN]", sanitized)
    sanitized = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]", sanitized)

    return sanitized


class ResourceLimiter:
    """Tracks and enforces bounded resource consumption during repository inspection."""

    def __init__(
        self,
        max_file_count: int,
        max_file_size_bytes: int,
        max_total_bytes: int,
        timeout_seconds: float,
    ) -> None:
        self.max_file_count = max_file_count
        self.max_file_size_bytes = max_file_size_bytes
        self.max_total_bytes = max_total_bytes
        self.timeout_seconds = timeout_seconds

        self.start_time = time.monotonic()
        self.scanned_file_count = 0
        self.scanned_total_bytes = 0

    def check_timeout(self) -> None:
        """Verify elapsed time has not exceeded the configured quota."""
        elapsed = time.monotonic() - self.start_time
        if elapsed > self.timeout_seconds:
            raise SnapshotTimeoutError(
                f"Inspection timed out after {elapsed:.1f}s (quota: {self.timeout_seconds}s)."
            )

    def register_file(self, file_path: str, size_bytes: int) -> bool:
        """Record a file and verify resource bounds.

        Returns True if the file should be analyzed, or raises ResourceLimitExceededError if hard bounds are hit.
        """
        self.check_timeout()

        if self.scanned_file_count >= self.max_file_count:
            raise ResourceLimitExceededError(
                f"Repository exceeded maximum file count limit ({self.max_file_count} files)."
            )

        if self.scanned_total_bytes + size_bytes > self.max_total_bytes:
            raise ResourceLimitExceededError(
                f"Repository exceeded maximum aggregate size limit ({self.max_total_bytes} bytes)."
            )

        self.scanned_file_count += 1
        self.scanned_total_bytes += size_bytes
        return True

    def is_file_size_permitted(self, size_bytes: int) -> bool:
        """Check if an individual file is within individual file size bounds."""
        return size_bytes <= self.max_file_size_bytes


def is_excluded_directory(dir_name: str) -> bool:
    """Check if a directory name is on the exclusion list."""
    return dir_name in EXCLUDED_DIRECTORIES or dir_name.startswith(".")


def is_binary_file(filename: str) -> bool:
    """Check if a filename has an excluded binary extension."""
    _, ext = os.path.splitext(filename)
    return ext.lower() in BINARY_EXTENSIONS
