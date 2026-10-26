"""Pydantic schemas for repository inspection requests and reports."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from oracle.inspection.ast_parser import FileSyntaxError
from oracle.inspection.detector import DetectedEcosystem
from oracle.inspection.graph import DependencyGraph


class InspectionOptions(BaseModel):
    """Optional execution parameters for a repository inspection run."""

    timeout_seconds: Optional[int] = Field(
        None, ge=1, le=300, description="Optional override for inspection timeout in seconds"
    )
    max_files: Optional[int] = Field(
        None, ge=1, le=10000, description="Optional override for maximum file count"
    )


class InspectionReport(BaseModel):
    """Complete static inspection report for a registered repository."""

    model_config = ConfigDict(from_attributes=True)

    repository_id: uuid.UUID = Field(..., description="Target repository UUID")
    status: str = Field(
        ...,
        description="Inspection outcome status: completed (full scan), partial (syntax errors or limits hit), failed (ingestion error)",
    )
    source_type: str = Field(..., description="Target source type (git or local_directory)")
    target_location: str = Field(..., description="Sanitized target URL or local directory location")
    commit_hash: Optional[str] = Field(None, description="Snapshot commit SHA if available")
    ecosystems: List[DetectedEcosystem] = Field(
        default_factory=list, description="Detected programming language ecosystems"
    )
    total_files_discovered: int = Field(default=0, ge=0)
    total_files_analyzed: int = Field(default=0, ge=0)
    total_bytes_analyzed: int = Field(default=0, ge=0)
    syntax_errors: List[FileSyntaxError] = Field(
        default_factory=list, description="File-level syntax errors encountered during AST parsing"
    )
    skipped_files: List[str] = Field(
        default_factory=list, description="Files skipped due to policy or size limits"
    )
    dependency_graph: DependencyGraph = Field(
        ..., description="Aggregated static dependency graph with provenance"
    )
    missing_evidence: List[str] = Field(
        default_factory=list, description="Signals that could not be verified (e.g. dynamic imports, unparsed non-Python code)"
    )
    error_message: Optional[str] = Field(
        None, description="Diagnostic error explanation if status is failed or partial"
    )
    started_at: datetime = Field(..., description="UTC start timestamp")
    completed_at: datetime = Field(..., description="UTC completion timestamp")
    duration_ms: float = Field(..., ge=0.0, description="Total execution duration in milliseconds")
