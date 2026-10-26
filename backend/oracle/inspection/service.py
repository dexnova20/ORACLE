"""Orchestration service for controlled repository snapshot ingestion and static inspection."""

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from oracle.core.config import settings
from oracle.inspection.ast_parser import ParsedFileSummary, parse_python_file
from oracle.inspection.detector import detect_ecosystems
from oracle.inspection.go_parser import (
    is_go_file,
    load_go_mod,
    parse_go_source,
)
from oracle.inspection.graph import DependencyGraph, build_dependency_graph
from oracle.inspection.java_parser import (
    is_java_file,
    parse_java_files_batch,
)
from oracle.inspection.policy import (
    InspectionPolicyError,
    PathTraversalError,
    ResourceLimiter,
    ResourceLimitExceededError,
    SnapshotTimeoutError,
    is_binary_file,
    is_excluded_directory,
    redact_secrets,
)
from oracle.inspection.snapshot import (
    SnapshotContext,
    ingest_git_repository,
    ingest_local_directory,
)
from oracle.inspection.ts_parser import (
    is_ts_js_file,
    load_package_json,
    load_tsconfig,
    parse_ts_files_batch,
)
from oracle.models.repository import Repository
from oracle.schemas.inspection import InspectionOptions, InspectionReport


class InspectionService:
    """Coordinates snapshot ingestion, ecosystem detection, AST parsing, and dependency mapping."""

    def __init__(self) -> None:
        # In-memory storage for latest inspection reports per repository
        self._reports: Dict[uuid.UUID, InspectionReport] = {}

    def get_latest_report(self, repository_id: uuid.UUID) -> Optional[InspectionReport]:
        """Retrieve the most recent inspection report for a registered repository."""
        return self._reports.get(repository_id)

    def inspect_repository(
        self,
        repository: Repository,
        options: Optional[InspectionOptions] = None,
    ) -> InspectionReport:
        """Execute safe, bounded static inspection on a registered repository target."""
        start_time_monotonic = time.monotonic()
        started_at = datetime.now(timezone.utc)

        timeout = (
            options.timeout_seconds
            if options and options.timeout_seconds is not None
            else settings.inspection_timeout_seconds
        )
        max_files = (
            options.max_files
            if options and options.max_files is not None
            else settings.max_inspection_file_count
        )

        limiter = ResourceLimiter(
            max_file_count=max_files,
            max_file_size_bytes=settings.max_inspection_file_size_bytes,
            max_total_bytes=settings.max_inspection_total_bytes,
            timeout_seconds=float(timeout),
        )

        snapshot_ctx: Optional[SnapshotContext] = None
        status = "completed"
        error_message: Optional[str] = None
        missing_evidence: List[str] = []
        skipped_files: List[str] = []

        try:
            # 1. Acquire repository snapshot
            if repository.source_type == "git":
                snapshot_ctx = ingest_git_repository(
                    git_url=repository.url,
                    timeout_seconds=float(timeout),
                )
            else:
                snapshot_ctx = ingest_local_directory(
                    local_path=repository.url,
                    permitted_roots=settings.permitted_local_roots,
                )

            root_dir = snapshot_ctx.root_path

            # 2. Enumerate repository files while respecting directory exclusions and resource limits
            discovered_rel_files: List[str] = []
            try:
                for current_dir, dir_names, filenames in os.walk(root_dir):
                    limiter.check_timeout()

                    # Prune excluded directories in-place so os.walk skips them
                    dir_names[:] = [d for d in dir_names if not is_excluded_directory(d)]

                    for fname in filenames:
                        full_path = os.path.join(current_dir, fname)
                        rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")

                        if is_binary_file(fname):
                            continue

                        try:
                            st = os.stat(full_path)
                            size = st.st_size
                        except OSError:
                            continue

                        try:
                            limiter.register_file(rel_path, size)
                            discovered_rel_files.append(rel_path)
                        except ResourceLimitExceededError as rle:
                            status = "partial"
                            error_message = str(rle)
                            skipped_files.append(rel_path)
                            break  # Stop adding more files once limit is exceeded

                    if status == "partial" and error_message and "maximum file count" in error_message:
                        break

            except SnapshotTimeoutError as te:
                status = "partial"
                error_message = str(te)

            # 3. Detect programming ecosystems based on discovered manifest files and source extensions
            ecosystems = detect_ecosystems(discovered_rel_files)
            unsupported_ecosystems = [
                e.name for e in ecosystems if e.name not in ("python", "javascript_typescript", "java_jvm", "go")
            ]
            if unsupported_ecosystems:
                missing_evidence.append(
                    f"Ecosystems without static AST support detected: {', '.join(unsupported_ecosystems)}. Deep AST inspection is supported for Python, TypeScript/JavaScript, Java, and Go."
                )

            # 4. Filter eligible source files for AST parsing
            all_py_files: Set[str] = {f for f in discovered_rel_files if f.endswith(".py")}
            all_ts_js_files: Set[str] = {f for f in discovered_rel_files if is_ts_js_file(f)}
            all_java_files: Set[str] = {f for f in discovered_rel_files if is_java_file(f)}
            all_go_files: Set[str] = {f for f in discovered_rel_files if is_go_file(f)}
            all_known_files_set: Set[str] = set(discovered_rel_files)

            parsed_summaries: List[ParsedFileSummary] = []
            analyzed_count = 0
            analyzed_bytes = 0

            # 4a. Parse Python source files
            for py_rel in sorted(all_py_files):
                limiter.check_timeout()
                full_py_path = os.path.join(root_dir, py_rel.replace("/", os.sep))

                try:
                    file_size = os.path.getsize(full_py_path)
                    if not limiter.is_file_size_permitted(file_size):
                        status = "partial"
                        skipped_files.append(py_rel)
                        continue

                    # Read file content safely as UTF-8 with fallback
                    with open(full_py_path, "r", encoding="utf-8", errors="replace") as f:
                        source_code = f.read()

                    summary = parse_python_file(py_rel, source_code, all_py_files)
                    parsed_summaries.append(summary)
                    analyzed_count += 1
                    analyzed_bytes += file_size

                    if summary.status == "syntax_error":
                        status = "partial"

                except Exception as ex:
                    status = "partial"
                    skipped_files.append(py_rel)

            # 4b. Parse TypeScript and JavaScript source files
            if all_ts_js_files:
                tsconfig = load_tsconfig(root_dir)
                package_json = load_package_json(root_dir)

                ts_items: List[Dict[str, str]] = []
                for ts_rel in sorted(all_ts_js_files):
                    limiter.check_timeout()
                    full_ts_path = os.path.join(root_dir, ts_rel.replace("/", os.sep))
                    try:
                        file_size = os.path.getsize(full_ts_path)
                        if not limiter.is_file_size_permitted(file_size):
                            status = "partial"
                            skipped_files.append(ts_rel)
                            continue
                        ts_items.append({"path": ts_rel})
                        analyzed_bytes += file_size
                    except Exception:
                        status = "partial"
                        skipped_files.append(ts_rel)

                if ts_items:
                    ts_summaries = parse_ts_files_batch(
                        files=ts_items,
                        all_known_files=all_known_files_set,
                        root_dir=root_dir,
                        tsconfig=tsconfig,
                        package_json=package_json,
                    )
                    for summary in ts_summaries:
                        parsed_summaries.append(summary)
                        analyzed_count += 1
                        if summary.status in ("syntax_error", "analysis_failed"):
                            status = "partial"

            # 4c. Parse Java source files
            if all_java_files:
                java_items: List[Dict[str, str]] = []
                for j_rel in sorted(all_java_files):
                    limiter.check_timeout()
                    full_j_path = os.path.join(root_dir, j_rel.replace("/", os.sep))
                    try:
                        file_size = os.path.getsize(full_j_path)
                        if not limiter.is_file_size_permitted(file_size):
                            status = "partial"
                            skipped_files.append(j_rel)
                            continue
                        java_items.append({"path": j_rel})
                        analyzed_bytes += file_size
                    except Exception:
                        status = "partial"
                        skipped_files.append(j_rel)

                if java_items:
                    java_summaries = parse_java_files_batch(
                        files=java_items,
                        all_known_files=all_known_files_set,
                        root_dir=root_dir,
                    )
                    for summary in java_summaries:
                        parsed_summaries.append(summary)
                        analyzed_count += 1
                        if summary.status in ("syntax_error", "analysis_failed"):
                            status = "partial"

            # 4d. Parse Go source files
            if all_go_files:
                go_manifest = load_go_mod(root_dir)
                for go_rel in sorted(all_go_files):
                    limiter.check_timeout()
                    full_go_path = os.path.join(root_dir, go_rel.replace("/", os.sep))
                    try:
                        file_size = os.path.getsize(full_go_path)
                        if not limiter.is_file_size_permitted(file_size):
                            status = "partial"
                            skipped_files.append(go_rel)
                            continue
                        with open(full_go_path, "r", encoding="utf-8", errors="replace") as f:
                            go_source = f.read()
                        summary = parse_go_source(
                            file_path=go_rel,
                            content=go_source,
                            module_manifest=go_manifest,
                            all_repo_files=all_known_files_set,
                            repo_root=root_dir,
                        )
                        parsed_summaries.append(summary)
                        analyzed_count += 1
                        analyzed_bytes += file_size
                        if summary.status in ("syntax_error", "analysis_failed"):
                            status = "partial"
                    except Exception:
                        status = "partial"
                        skipped_files.append(go_rel)

            # 5. Build static dependency graph with provenance
            dependency_graph = build_dependency_graph(parsed_summaries)

            # Aggregate syntax errors
            syntax_errors = [s.syntax_error for s in parsed_summaries if s.syntax_error is not None]

            # Collect unparsed external references
            if dependency_graph.unresolved_edge_count > 0:
                missing_evidence.append(
                    f"{dependency_graph.unresolved_edge_count} unresolved relative imports detected (candidate missing files or dynamic references)."
                )

            completed_at = datetime.now(timezone.utc)
            duration_ms = (time.monotonic() - start_time_monotonic) * 1000.0

            report = InspectionReport(
                repository_id=repository.id,
                status=status,
                source_type=repository.source_type,
                target_location=redact_secrets(repository.url),
                commit_hash=snapshot_ctx.commit_hash,
                ecosystems=ecosystems,
                total_files_discovered=len(discovered_rel_files),
                total_files_analyzed=analyzed_count,
                total_bytes_analyzed=analyzed_bytes,
                syntax_errors=syntax_errors,
                skipped_files=skipped_files,
                dependency_graph=dependency_graph,
                missing_evidence=missing_evidence,
                error_message=redact_secrets(error_message) if error_message else None,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=round(duration_ms, 2),
            )

        except (InspectionPolicyError, PathTraversalError, FileNotFoundError) as err:
            completed_at = datetime.now(timezone.utc)
            duration_ms = (time.monotonic() - start_time_monotonic) * 1000.0
            report = InspectionReport(
                repository_id=repository.id,
                status="failed",
                source_type=repository.source_type,
                target_location=redact_secrets(repository.url),
                commit_hash=None,
                ecosystems=[],
                total_files_discovered=0,
                total_files_analyzed=0,
                total_bytes_analyzed=0,
                syntax_errors=[],
                skipped_files=[],
                dependency_graph=DependencyGraph(),
                missing_evidence=["Ingestion failed before AST analysis"],
                error_message=redact_secrets(str(err)),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=round(duration_ms, 2),
            )

        finally:
            if snapshot_ctx:
                snapshot_ctx.cleanup()

        # Cache report
        self._reports[repository.id] = report
        return report


inspection_service = InspectionService()
