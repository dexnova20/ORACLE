"""Versioned schema and target-leakage safeguards for diagnostic experiment datasets."""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ml.taxonomy.fault_taxonomy import FaultCategory

DATASET_SCHEMA_VERSION = "1.0.0"

# Target leakage patterns that must never appear in raw model input features
FORBIDDEN_FEATURE_PATTERNS = [
    re.compile(r"\broot_cause\b", re.IGNORECASE),
    re.compile(r"\bground_truth\b", re.IGNORECASE),
    re.compile(r"\binjected_fault\b", re.IGNORECASE),
]


class ObservedSymptom(BaseModel):
    """An observable symptom signal captured during system execution or test."""

    model_config = ConfigDict(frozen=True)

    symptom_type: str = Field(
        ...,
        description="Signal type (e.g. log_error, http_status, exit_code, exception)",
        examples=["log_error"],
    )
    source: str = Field(
        ...,
        description="Originating component or probe (e.g. backend_api, test_runner, nginx)",
        examples=["backend_api"],
    )
    message_pattern: str = Field(
        ...,
        description="Sanitized symptom message or regex signature without target leaks",
        examples=["ConnectionRefusedError: [Errno 111] Connection refused"],
    )
    severity: str = Field(
        default="error",
        description="Symptom severity (info, warning, error, critical)",
    )
    timestamp_offset_ms: Optional[float] = Field(
        default=None,
        description="Relative millisecond offset from the start of the diagnostic observation window",
    )

    @field_validator("message_pattern")
    @classmethod
    def check_message_for_target_leakage(cls, v: str) -> str:
        for pattern in FORBIDDEN_FEATURE_PATTERNS:
            if pattern.search(v):
                raise ValueError(
                    f"Target leakage detected in symptom message: pattern '{pattern.pattern}' is forbidden."
                )
        return v


class TestResultFeature(BaseModel):
    """Summary of an automated test execution result used as a diagnostic feature."""

    __test__ = False

    model_config = ConfigDict(frozen=True)

    test_id: str = Field(..., description="Unique test case identifier or path")
    passed: bool = Field(..., description="Whether the test passed")
    duration_ms: float = Field(..., ge=0.0, description="Execution duration in milliseconds")
    error_type: Optional[str] = Field(None, description="Exception class name if failed")
    error_message_snippet: Optional[str] = Field(
        None,
        description="Truncated stack trace or assertion error message",
    )

    @field_validator("error_message_snippet")
    @classmethod
    def check_snippet_for_leakage(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            for pattern in FORBIDDEN_FEATURE_PATTERNS:
                if pattern.search(v):
                    raise ValueError(
                        f"Target leakage detected in test snippet: pattern '{pattern.pattern}' is forbidden."
                    )
        return v


class TelemetryFeatures(BaseModel):
    """Quantitative performance and resource metrics observed during incident."""

    model_config = ConfigDict(frozen=True)

    latency_p50_ms: Optional[float] = Field(None, ge=0.0, description="Median response latency in ms")
    latency_p95_ms: Optional[float] = Field(None, ge=0.0, description="95th percentile latency in ms")
    error_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Fraction of failed requests")
    cpu_utilization_pct: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="CPU usage percentage across cores"
    )
    memory_rss_mb: Optional[float] = Field(None, ge=0.0, description="Resident Set Size memory in MB")


class CaseFeatures(BaseModel):
    """Container for all model input features.

    Strictly isolated from ground-truth labels and expected diagnostic outcomes.
    """

    model_config = ConfigDict(frozen=True)

    symptoms: List[ObservedSymptom] = Field(
        default_factory=list,
        description="List of observed symptoms, log signatures, or error events",
    )
    component_identifiers: List[str] = Field(
        default_factory=list,
        description="Identifiers of software components under inspection",
    )
    dependency_identifiers: List[str] = Field(
        default_factory=list,
        description="Identifiers of external dependencies (e.g. postgresql, redis)",
    )
    test_results: List[TestResultFeature] = Field(
        default_factory=list,
        description="Results of tests executed during the diagnostic probe",
    )
    telemetry: Optional[TelemetryFeatures] = Field(
        default=None,
        description="Quantitative resource metrics if available",
    )
    missing_evidence_indicators: List[str] = Field(
        default_factory=list,
        description="Explicit list of diagnostic signals that were queried but absent (e.g. db_query_log, flamegraph)",
    )


class GroundTruthLabel(BaseModel):
    """Injected or verified ground-truth diagnosis.

    Stored in an isolated structure to prevent target leakage into model inputs.
    """

    model_config = ConfigDict(frozen=True)

    root_cause_category: FaultCategory = Field(
        ...,
        description="The true fault taxonomy category established as ground truth",
    )
    root_cause_component: str = Field(
        ...,
        description="The specific component or module where the fault originated",
    )
    root_cause_detail: str = Field(
        ...,
        description="Detailed forensic explanation of the failure mechanism",
    )
    injection_method: Optional[str] = Field(
        None,
        description="How the fault was induced (e.g. port_closed, missing_env, mutation, organic)",
    )
    verified: bool = Field(
        default=True,
        description="Whether this ground-truth diagnosis was empirically verified",
    )


class ExpectedDiagnosticOutcome(BaseModel):
    """The ideal remediation or diagnostic step expected from the system."""

    model_config = ConfigDict(frozen=True)

    primary_action: str = Field(
        ...,
        description="Recommended resolution action (e.g. START_POSTGRES_SERVICE, MIGRATE_SCHEMA, ABSTAIN_INSUFFICIENT_EVIDENCE)",
    )
    recommended_probes: List[str] = Field(
        default_factory=list,
        description="Further diagnostic tests or probes that would verify the diagnosis",
    )
    urgency: str = Field(
        default="medium",
        description="Action urgency level (low, medium, high, critical)",
    )


class ProvenanceMetadata(BaseModel):
    """Audit provenance and reproducibility metadata for diagnostic cases."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    schema_version: str = Field(
        default=DATASET_SCHEMA_VERSION,
        description="Dataset schema version",
    )
    git_commit: Optional[str] = Field(
        default=None,
        description="Git commit SHA of the codebase when the case was captured",
    )
    generator_info: str = Field(
        default="ORACLE Diagnostic Framework",
        description="Tool or script that generated the experiment case",
    )
    platform: str = Field(
        default="generic",
        description="Operating system or runtime platform info",
    )


class DiagnosticCase(BaseModel):
    """A self-contained, reproducible diagnostic experiment record."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(..., description="Unique case identifier (UUID or deterministic hash)")
    project_id: str = Field(
        ...,
        description="Software project or repository identifier (used for group-aware evaluation splitting)",
    )
    scenario_id: str = Field(
        ...,
        description="Fault scenario identifier (used for scenario-aware evaluation splitting)",
    )
    is_synthetic: bool = Field(
        default=True,
        description="Explicit flag marking whether this case is a synthetic/fixture example. Must be True for synthetic data.",
    )
    provenance: ProvenanceMetadata = Field(
        default_factory=ProvenanceMetadata,
        description="Case creation provenance metadata",
    )
    features: CaseFeatures = Field(
        ...,
        description="Model input features (strictly isolated from ground-truth labels)",
    )
    ground_truth: GroundTruthLabel = Field(
        ...,
        description="Ground-truth root cause label (never exposed to model during inference)",
    )
    expected_outcome: ExpectedDiagnosticOutcome = Field(
        ...,
        description="Expected diagnostic action and recommended probes",
    )

    @model_validator(mode="after")
    def verify_target_leakage_safeguard(self) -> "DiagnosticCase":
        """Assert that ground-truth details are not smuggled into observable features."""
        gt_detail = self.ground_truth.root_cause_detail.lower().strip()
        if len(gt_detail) > 10:
            for symptom in self.features.symptoms:
                if gt_detail in symptom.message_pattern.lower():
                    raise ValueError(
                        f"Target leakage detected: ground_truth.root_cause_detail was found verbatim in symptom message!"
                    )
        return self

    def to_model_features(self) -> Dict[str, Any]:
        """Extract purely model input features.

        Guarantees that ground_truth and expected_outcome are omitted from the returned payload,
        preventing target leakage at the training and evaluation boundaries.
        """
        return self.features.model_dump()

    def get_ground_truth_category(self) -> FaultCategory:
        """Access the ground truth label explicitly."""
        return self.ground_truth.root_cause_category
