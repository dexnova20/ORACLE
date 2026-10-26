"""Target code ingestion, static analysis, and ecosystem inspection module."""

from oracle.inspection.policy import (
    EXCLUDED_DIRECTORIES,
    BINARY_EXTENSIONS,
    InspectionPolicyError,
    PathTraversalError,
    ResourceLimitExceededError,
    SnapshotTimeoutError,
    ResourceLimiter,
    redact_secrets,
)
from oracle.inspection.snapshot import (
    SnapshotContext,
    ingest_local_directory,
    ingest_git_repository,
    resolve_permitted_roots,
)
from oracle.inspection.detector import (
    DetectedEcosystem,
    detect_ecosystems,
)
from oracle.inspection.ast_parser import (
    ImportRecord,
    FileSyntaxError,
    ParsedFileSummary,
    parse_python_file,
)
from oracle.inspection.graph import (
    DependencyNode,
    DependencyEdge,
    DependencyGraph,
    build_dependency_graph,
)
def __getattr__(name: str):
    if name == "InspectionService":
        from oracle.inspection.service import InspectionService
        return InspectionService
    if name == "inspection_service":
        from oracle.inspection.service import inspection_service
        return inspection_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "EXCLUDED_DIRECTORIES",
    "BINARY_EXTENSIONS",
    "InspectionPolicyError",
    "PathTraversalError",
    "ResourceLimitExceededError",
    "SnapshotTimeoutError",
    "ResourceLimiter",
    "redact_secrets",
    "SnapshotContext",
    "ingest_local_directory",
    "ingest_git_repository",
    "resolve_permitted_roots",
    "DetectedEcosystem",
    "detect_ecosystems",
    "ImportRecord",
    "FileSyntaxError",
    "ParsedFileSummary",
    "parse_python_file",
    "DependencyNode",
    "DependencyEdge",
    "DependencyGraph",
    "build_dependency_graph",
    "InspectionService",
    "inspection_service",
]
