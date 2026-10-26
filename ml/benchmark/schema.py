"""Typed contracts, evidence representation, and ground-truth isolation for ORACLE benchmarks."""

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ml.taxonomy.fault_taxonomy import FaultCategory, TAXONOMY_VERSION

BENCHMARK_SCHEMA_VERSION = "1.0.0"

# Target leakage patterns that must never appear in diagnostic input features or evidence
FORBIDDEN_EVIDENCE_PATTERNS = [
    re.compile(r"\broot_cause\b", re.IGNORECASE),
    re.compile(r"\bground_truth\b", re.IGNORECASE),
    re.compile(r"\binjected_fault\b", re.IGNORECASE),
]


class EvidenceState(str, Enum):
    """Classification of diagnostic evidence state."""

    OBSERVED = "observed"
    INFERRED = "inferred"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


class DiagnosticEvidence(BaseModel):
    """Observable evidence genuinely captured during static code inspection.

    Strictly isolated from ground truth, injected-fault details, and expected outcomes.
    """

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(..., description="Neutral scenario identifier (e.g. CASE-001)")
    project_id: str = Field(..., description="Neutral project identifier (e.g. PRJ-001)")
    status: str = Field(..., description="Inspection status: completed, partial, or failed")
    ecosystems: List[str] = Field(default_factory=list, description="Detected language ecosystems")
    total_files_discovered: int = Field(default=0, ge=0)
    total_files_analyzed: int = Field(default=0, ge=0)
    syntax_errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Captured file syntax errors with line numbers and messages",
    )
    unresolved_imports: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Captured unresolved imports with source and line provenance",
    )
    external_imports: List[str] = Field(
        default_factory=list,
        description="Captured external package imports",
    )
    missing_evidence: List[str] = Field(
        default_factory=list,
        description="Signals or probe results queried but absent or unsupported",
    )
    evidence_state: EvidenceState = Field(
        default=EvidenceState.OBSERVED,
        description="State classification of this evidence record",
    )
    duration_ms: float = Field(default=0.0, ge=0.0)
    provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Inspection tool, inspector version, and commit hash provenance",
    )

    @field_validator("missing_evidence")
    @classmethod
    def check_missing_evidence_for_leakage(cls, items: List[str]) -> List[str]:
        for item in items:
            for pattern in FORBIDDEN_EVIDENCE_PATTERNS:
                if pattern.search(item):
                    raise ValueError(
                        f"Target leakage detected in missing_evidence: pattern '{pattern.pattern}' is forbidden."
                    )
        return items

    def to_diagnostic_input(self) -> Dict[str, Any]:
        """Serialize purely observable evidence for consumption by diagnostic algorithms.

        Guarantees that ground truth, injected-fault labels, and expected outcomes
        are physically omitted from the payload.
        """
        payload = self.model_dump()
        # Verify no forbidden target leakage tokens were smuggled into the dictionary
        serialized = str(payload)
        for pattern in FORBIDDEN_EVIDENCE_PATTERNS:
            if pattern.search(serialized):
                raise ValueError(
                    f"Leakage check failed: pattern '{pattern.pattern}' detected in serialized diagnostic input."
                )
        return payload


class BenchmarkScenario(BaseModel):
    """Specification of a controlled benchmark scenario presented to the diagnostic pipeline.

    Does NOT contain ground truth or expected outcomes.
    """

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(..., description="Neutral identifier (e.g. CASE-001)")
    project_id: str = Field(..., description="Neutral project identifier (e.g. PRJ-001)")
    fixture_relative_path: str = Field(..., description="Path to fixture project on disk")
    is_healthy_control: bool = Field(default=False, description="Whether this is a non-faulty baseline")
    is_supported_statically: bool = Field(
        default=True,
        description="Whether ORACLE's static inspector has capabilities to observe this scenario",
    )
    unsupported_reason: Optional[str] = Field(
        default=None,
        description="Explanation if static inspection cannot observe the scenario (e.g. requires dynamic execution)",
    )
    reproduction_method: str = Field(..., description="How to reproduce the scenario")
    safety_classification: str = Field(
        default="safe_static_only",
        description="Safety boundary (e.g. safe_static_only, sandboxed_exec_required)",
    )
    benchmark_version: str = Field(default=BENCHMARK_SCHEMA_VERSION)

    @field_validator("scenario_id", "project_id")
    @classmethod
    def check_neutral_identifiers(cls, v: str) -> str:
        for pattern in FORBIDDEN_EVIDENCE_PATTERNS:
            if pattern.search(v):
                raise ValueError(f"Identifier '{v}' contains forbidden target label or leakage keyword.")
        return v


class ScenarioGroundTruth(BaseModel):
    """Separately stored ground-truth diagnosis and remediation expectation.

    Must NEVER be serialized into diagnostic input or exposed to inspection code.
    """

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(..., description="Target scenario identifier (e.g. CASE-001)")
    taxonomy_category: Optional[FaultCategory] = Field(
        default=None,
        description="Ground-truth fault category (None if healthy control)",
    )
    taxonomy_version: str = Field(default=TAXONOMY_VERSION)
    root_cause_component: str = Field(..., description="Component responsible for fault")
    injected_fault_description: str = Field(..., description="Technical description of injected fault")
    expected_observable_evidence: List[str] = Field(
        default_factory=list,
        description="Specific signals the inspector is expected to extract",
    )
    expected_diagnostic_outcome: str = Field(
        ...,
        description="Expected resolution or diagnosis (e.g. FIX_SYNTAX_ERROR, RESOLVE_IMPORT, CLEAN_NO_FAULT, ABSTAIN)",
    )
    plausible_confounding_explanations: List[str] = Field(
        default_factory=list,
        description="Alternative diagnoses that could explain the symptoms",
    )
    required_evidence_for_confidence: List[str] = Field(
        default_factory=list,
        description="Signals strictly required before a confident diagnosis can be made",
    )
    abstention_conditions: List[str] = Field(
        default_factory=list,
        description="Conditions under which the diagnostic system must abstain",
    )


class GroundTruthManifest(BaseModel):
    """Container for all scenario ground-truth records.

    Maintained independently of diagnostic input structures.
    """

    model_config = ConfigDict(frozen=True)

    manifest_version: str = Field(default=BENCHMARK_SCHEMA_VERSION)
    entries: Dict[str, ScenarioGroundTruth] = Field(
        ...,
        description="Dictionary mapping neutral scenario_id to ScenarioGroundTruth",
    )

    def get(self, scenario_id: str) -> Optional[ScenarioGroundTruth]:
        """Retrieve ground truth for a scenario by neutral identifier."""
        return self.entries.get(scenario_id)

    def contains(self, scenario_id: str) -> bool:
        """Check whether ground truth exists for a scenario."""
        return scenario_id in self.entries


class BenchmarkCaseResult(BaseModel):
    """Evaluation result for a single benchmark scenario."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    project_id: str
    is_supported_statically: bool
    evidence: DiagnosticEvidence
    observed_fault_category: Optional[FaultCategory] = None
    evaluation_outcome: str = Field(
        ...,
        description="Outcome: correct, correct_control, false_positive, correct_abstention, incorrect_abstention, unsupported_analysis, incorrect",
    )
    explanation: str


class BenchmarkRunSummary(BaseModel):
    """Aggregate benchmark results and evaluation metrics."""

    model_config = ConfigDict(frozen=True)

    benchmark_version: str = BENCHMARK_SCHEMA_VERSION
    run_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_scenarios: int
    supported_scenarios: int
    unsupported_scenarios: int
    healthy_controls_count: int
    false_positive_count: int
    false_positive_rate: float
    evidence_extraction_coverage: float
    abstention_count: int
    correct_abstentions: int
    static_diagnostic_accuracy: float
    top_k_ranking_accuracy: Optional[float] = None
    macro_precision: Optional[float] = None
    macro_recall: Optional[float] = None
    macro_f1: Optional[float] = None
    case_results: List[BenchmarkCaseResult]
