"""Pydantic schemas for sandboxed dynamic test execution requests and reports."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ExecutionState(str, Enum):
    """Lifecycle states for dynamic test execution."""

    RUNNING = "running"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"
    REJECTED_BY_POLICY = "rejected_by_policy"
    ISOLATION_UNAVAILABLE = "isolation_unavailable"
    FAILED = "failed"
    PARTIAL = "partial"


class ExecutionRequest(BaseModel):
    """Client request to trigger dynamic test execution."""

    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(
        ...,
        description="Approved workload profile ID from the ORACLE allowlist",
        examples=["benchmark-db-probe", "benchmark-env-audit"],
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        le=60,
        description="Optional timeout override (clamped to max policy limit)",
    )


class ExecutionReport(BaseModel):
    """Complete forensic report of a sandboxed dynamic execution run."""

    model_config = ConfigDict(frozen=True)

    execution_id: uuid.UUID = Field(..., description="Unique run identifier")
    repository_id: uuid.UUID = Field(..., description="Target repository primary key")
    profile_id: str = Field(..., description="Executed workload profile identifier")
    status: ExecutionState = Field(..., description="Final execution lifecycle state")
    exit_code: Optional[int] = Field(None, description="Process exit code (0 = success, non-zero = failure)")
    stdout: str = Field(default="", description="Sanitized standard output within byte limits")
    stderr: str = Field(default="", description="Sanitized standard error within byte limits")
    output_truncated: bool = Field(default=False, description="Whether output exceeded byte quotas and was capped")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds")
    applied_isolation_controls: List[str] = Field(
        default_factory=list,
        description="Security controls enforced during execution",
    )
    termination_reason: Optional[str] = Field(
        default=None,
        description="Forensic explanation of how/why execution terminated",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Redacted error description if execution failed or was rejected",
    )
    provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Worker, provider, and policy version provenance",
    )
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
