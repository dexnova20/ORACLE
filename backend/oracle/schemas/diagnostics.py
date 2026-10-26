"""Pydantic schemas and typed contracts for ORACLE diagnostic workflow and reports."""

from datetime import datetime, timezone
import enum
import os
import sys
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator

# Ensure root is in sys.path so ml.taxonomy can be imported
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from ml.taxonomy.fault_taxonomy import FAULT_TAXONOMY, FaultCategory


class DiagnosticStage(str, enum.Enum):
    """Stages of the unified end-to-end diagnostic workflow."""

    VALIDATE_TARGET = "validate_target"
    ACQUIRE_SNAPSHOT = "acquire_snapshot"
    STATIC_INSPECTION = "static_inspection"
    BUILD_SYSTEM_MAP = "build_system_map"
    COLLECT_EVIDENCE = "collect_evidence"
    GENERATE_HYPOTHESES = "generate_hypotheses"
    PLAN_ADAPTIVE_PROBES = "plan_adaptive_probes"
    VERIFY_HYPOTHESES = "verify_hypotheses"
    GENERATE_REPORT = "generate_report"


class DiagnosticRunState(str, enum.Enum):
    """Lifecycle states for a diagnostic execution run."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DiagnosticComponent(BaseModel):
    """A technical component discovered within the target repository."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Stable unique identifier for the component (e.g. file:app.py, pkg:fastapi)")
    name: str = Field(..., description="Display name of the component")
    component_type: str = Field(
        ...,
        description="Component classification: source_file, internal_module, external_package, stdlib_module, unresolved_reference",
    )
    file_path: Optional[str] = Field(None, description="Relative file path if backed by an analyzed file")
    status: str = Field(
        ...,
        description="Analysis state: analyzed, syntax_error, unresolved, unsupported",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Component-level metadata and metrics")


class DiagnosticDependencyEdge(BaseModel):
    """Directed dependency relationship between two components in the system map."""

    model_config = ConfigDict(frozen=True)

    source_component_id: str = Field(..., description="Originating source component ID")
    target_component_id: str = Field(..., description="Target dependency component ID")
    dependency_type: str = Field(
        ...,
        description="Classification: stdlib, internal, external, unresolved",
    )
    line_number: Optional[int] = Field(None, description="Source line number where dependency is declared")
    import_statement: Optional[str] = Field(None, description="Exact import statement with provenance")
    is_resolved: bool = Field(True, description="Whether the dependency was successfully resolved to a concrete module")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Extraction provenance details")


class DiagnosticSystemMap(BaseModel):
    """Normalized technical component and dependency graph of the target system."""

    model_config = ConfigDict(frozen=True)

    components: List[DiagnosticComponent] = Field(default_factory=list, description="Discovered technical components")
    edges: List[DiagnosticDependencyEdge] = Field(default_factory=list, description="Observed dependency relationships")
    total_components: int = Field(default=0, ge=0)
    total_dependencies: int = Field(default=0, ge=0)
    internal_dependency_count: int = Field(default=0, ge=0)
    external_dependency_count: int = Field(default=0, ge=0)
    unresolved_dependency_count: int = Field(default=0, ge=0)
    syntax_error_component_count: int = Field(default=0, ge=0)


class DiagnosticEvidenceRecord(BaseModel):
    """Empirical signal or observable evidence collected during inspection or execution."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(..., description="Unique evidence identifier (e.g. EVID-SYNTAX-001)")
    evidence_type: str = Field(
        ...,
        description="Type of evidence: syntax_error, unresolved_import, undeclared_external_dependency, empty_codebase, isolation_preflight, execution_output",
    )
    source_component: str = Field(..., description="Originating component ID or subsystem")
    extraction_method: str = Field(
        ...,
        description="Extraction method: ast_parser, dependency_graph, manifest_audit, isolation_probe, worker_execution",
    )
    location: Optional[str] = Field(None, description="File path and line coordinate (e.g. service.py:12)")
    observed_data: Dict[str, Any] = Field(default_factory=dict, description="Sanitized observed payload")
    reliability: str = Field(
        default="direct_observation",
        description="Reliability level: direct_observation, inferred_signal, limited_context",
    )
    limitations: List[str] = Field(default_factory=list, description="Known context limits or ambiguities")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC collection timestamp",
    )


class FaultHypothesis(BaseModel):
    """Candidate fault explanation generated from empirical evidence without benchmark leakage."""

    model_config = ConfigDict(frozen=True)

    hypothesis_id: str = Field(..., description="Stable hypothesis identifier (e.g. HYPO-001)")
    category: FaultCategory = Field(..., description="Taxonomy fault category")
    category_title: str = Field(..., description="Human-readable title from fault taxonomy")
    affected_component: str = Field(..., description="Suspected component identifier or file path")
    supporting_evidence_ids: List[str] = Field(
        default_factory=list,
        description="IDs of empirical evidence records directly supporting this hypothesis",
    )
    contradicting_evidence_ids: List[str] = Field(
        default_factory=list,
        description="IDs of evidence contradicting or narrowing this hypothesis",
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Required assumptions for this hypothesis to hold",
    )
    alternative_explanations: List[str] = Field(
        default_factory=list,
        description="Plausible confounding root causes that could yield similar symptoms",
    )
    confidence_level: str = Field(
        default="uncertain",
        description="Empirically supported confidence: high, medium, low, uncertain",
    )
    relative_ranking_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Relative heuristic ranking score (NOT a calibrated probability)",
    )
    score_rationale: str = Field(
        default="",
        description="Explanation of how the relative score was computed",
    )
    verification_status: str = Field(
        default="not_verified",
        description="Verification outcome: candidate, supported, verified, partially_verified, contradicted, not_verified, blocked, unsupported, insufficient_evidence",
    )
    remediation_suggestion: Optional[str] = Field(
        None,
        description="Actionable, safe next diagnostic or remediation step",
    )
    uncertainty_reason: Optional[str] = Field(
        None,
        description="Identified uncertainty or missing evidence",
    )
    abstention_reason: Optional[str] = Field(
        None,
        description="Explanation if diagnostic engine abstains due to insufficient evidence",
    )


class DiagnosticProbe(BaseModel):
    """Potential diagnostic check to distinguish competing hypotheses or gather missing evidence."""

    model_config = ConfigDict(frozen=True)

    probe_id: str = Field(..., description="Unique probe identifier (e.g. PROBE-001)")
    probe_type: str = Field(
        ...,
        description="Type of probe: static_ast_syntax_check, static_import_resolution_check, static_manifest_audit, isolated_runtime_env_audit, isolated_db_socket_probe, isolated_contract_check, isolated_transform_test, downstream_independent_check",
    )
    target_component: str = Field(..., description="Target component ID or file path subject to probing (e.g. file:app.py, pkg:requests)")
    prerequisites: List[str] = Field(default_factory=list, description="Required prerequisites or evidence prior to probe execution")
    target_hypothesis_ids: List[str] = Field(default_factory=list, description="Hypotheses this probe is designed to distinguish or test")
    expected_outcomes: List[str] = Field(default_factory=list, description="Possible observable outcomes and their interpretation")
    estimated_cost: float = Field(default=1.0, ge=0.0, description="Heuristic execution cost estimate")
    cost_label: str = Field(default="heuristic_estimate", description="Clear label indicating whether cost is measured or heuristic")
    safety_classification: str = Field(
        default="safe_static_analysis",
        description="Classification: safe_static_analysis, sandboxed_container_execution, unsafe_host_execution",
    )
    requires_dynamic: bool = Field(default=False, description="Whether this probe requires sandboxed containerized dynamic execution")
    availability_status: str = Field(
        default="available",
        description="Status: available, unavailable_no_docker, unauthorized, prerequisites_unmet, rejected_by_policy",
    )
    selection_reason: Optional[str] = Field(None, description="Rationale explaining why the planner selected this probe")
    rejection_reason: Optional[str] = Field(None, description="Rationale if probe was rejected due to safety or policy")


class ProbeResult(BaseModel):
    """Recorded outcome of executing a diagnostic probe."""

    model_config = ConfigDict(frozen=True)

    probe_id: str = Field(..., description="ID of the executed probe (e.g. PROBE-001)")
    probe_type: str = Field(default="", description="Type of executed probe")
    run_id: uuid.UUID = Field(..., description="Associated diagnostic execution run UUID")
    target_component: str = Field(..., description="Target component probed")
    outcome: str = Field(..., description="Result outcome: confirmed, refuted, inconclusive, unsupported, failed")
    generated_evidence_ids: List[str] = Field(default_factory=list, description="IDs of newly generated evidence records produced by this probe")
    execution_status: str = Field(..., description="Execution status: completed, skipped, failed, timed_out, unsupported")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Measured execution duration")
    unsupported_reason: Optional[str] = Field(None, description="Explanation if probe execution was unsupported or skipped")
    applied_safety_policy: str = Field(default="standard_inspection_policy", description="Safety boundaries and isolation controls applied")
    ranking_changed: bool = Field(default=False, description="Whether this probe result altered the hypothesis ranking")
    details: str = Field(..., description="Forensic details and observations from the probe")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC completion timestamp")


class DiagnosticDecisionRecord(BaseModel):
    """Decision record explaining planner actions at an adaptive investigation iteration."""

    model_config = ConfigDict(frozen=True)

    iteration: int = Field(..., ge=1, description="Investigation iteration counter")
    decision_type: str = Field(
        ...,
        description="Decision type: select_probe, stop_investigation, reject_unsafe_probe, deliberate_abstention",
    )
    selected_probe_id: Optional[str] = Field(None, description="Probe selected for execution in this iteration")
    rationale: str = Field(..., description="Explainable rationale justifying the decision")
    candidates_considered_count: int = Field(default=0, ge=0, description="Number of candidate probes evaluated in this iteration")
    remaining_uncertainty: Optional[str] = Field(None, description="Summary of remaining diagnostic uncertainty")
    stopping_reason: Optional[str] = Field(
        None,
        description="Stopping rationale if loop terminated (e.g. sufficient_evidence_verified, budget_exhausted, no_useful_probe_available, further_investigation_unsafe_or_unsupported, deliberate_abstention)",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC decision timestamp")


class VerificationOutcome(BaseModel):
    """Result of attempting independent verification of a fault hypothesis."""

    model_config = ConfigDict(frozen=True)

    hypothesis_id: str = Field(..., description="ID of hypothesis subjected to verification")
    method: str = Field(
        ...,
        description="Verification method: static_ast_validation, container_sandbox, isolation_preflight, manifest_audit",
    )
    status: str = Field(
        ...,
        description="Outcome: verified, partially_verified, not_verified, blocked, unsupported",
    )
    workload_profile: Optional[str] = Field(None, description="Approved workload profile if dynamic execution was run")
    exit_code: Optional[int] = Field(None, description="Process exit code if workload executed")
    details: str = Field(..., description="Specific verification findings or why verification was blocked/unsupported")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC completion timestamp",
    )


class DiagnosticRunRequest(BaseModel):
    """Payload to initiate a new diagnostic run on a registered target."""

    capabilities: List[str] = Field(
        default_factory=lambda: [
            "static_inspection",
            "system_map",
            "evidence_collection",
            "hypothesis_generation",
            "dynamic_verification",
            "adaptive_probing",
        ],
        description="Requested diagnostic analysis capabilities",
    )
    allow_dynamic: bool = Field(
        default=False,
        description="Explicit user authorization for containerized dynamic workload execution",
    )
    workload_profile: Optional[str] = Field(
        None,
        description="Explicit allowlisted workload profile ID if dynamic verification is requested",
    )
    timeout_seconds: Optional[int] = Field(
        None, ge=1, le=600, description="Optional override for inspection and execution timeout"
    )
    max_files: Optional[int] = Field(
        None, ge=1, le=10000, description="Optional override for maximum file count"
    )
    max_iterations: Optional[int] = Field(
        default=5, ge=1, le=20, description="Maximum iterations for the adaptive diagnostic loop"
    )
    symptom_description: Optional[str] = Field(
        None,
        description="Optional observed symptom text, error message, or log snippet providing runtime context",
    )
    runtime_traceback: Optional[str] = Field(
        None,
        description="Optional captured stack trace or traceback string from runtime failure",
    )


class DiagnosticProbesResponse(BaseModel):
    """API response model for diagnostic probes inspection."""

    model_config = ConfigDict(from_attributes=True)

    run_id: uuid.UUID = Field(..., description="Diagnostic run UUID")
    candidate_probes: List[DiagnosticProbe] = Field(default_factory=list, description="All evaluated candidate probes")
    executed_probes: List[ProbeResult] = Field(default_factory=list, description="All executed probe results")
    stopping_reason: Optional[str] = Field(None, description="Explanation for loop termination")


class DiagnosticDecisionsResponse(BaseModel):
    """API response model for adaptive investigation decisions."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    run_id: uuid.UUID = Field(..., description="Diagnostic run UUID")
    decisions: List[DiagnosticDecisionRecord] = Field(default_factory=list, description="Sequential decision records")
    investigation_history: Optional[List[DiagnosticDecisionRecord]] = Field(
        None, description="Alias for decisions (for frontend contract compatibility)"
    )
    stopping_reason: Optional[str] = Field(None, description="Explanation for loop termination")

    @model_validator(mode="after")
    def sync_history_and_decisions(self) -> "DiagnosticDecisionsResponse":
        if self.investigation_history is None and self.decisions:
            object.__setattr__(self, "investigation_history", list(self.decisions))
        elif not self.decisions and self.investigation_history:
            object.__setattr__(self, "decisions", list(self.investigation_history))
        return self


class DiagnosticReport(BaseModel):
    """Complete diagnostic report synthesizing evidence, system map, hypotheses, and verification."""

    model_config = ConfigDict(from_attributes=True)

    run_id: uuid.UUID = Field(..., description="Unique diagnostic run UUID")
    repository_id: uuid.UUID = Field(..., description="Target repository UUID")
    repository_name: str = Field(..., description="Target repository display name")
    repository_url: str = Field(..., description="Sanitized repository location or URL")
    source_type: str = Field(..., description="Source type (git or local_directory)")
    commit_hash: Optional[str] = Field(None, description="Snapshot commit SHA if available")
    status: str = Field(..., description="Run outcome: completed, partial, failed")
    completed_stages: List[str] = Field(default_factory=list, description="Stages successfully executed")
    unsupported_stages: List[str] = Field(default_factory=list, description="Stages that could not run")
    system_map: DiagnosticSystemMap = Field(..., description="Constructed component and dependency graph")
    evidence: List[DiagnosticEvidenceRecord] = Field(default_factory=list, description="Discrete evidence records")
    hypotheses: List[FaultHypothesis] = Field(default_factory=list, description="Generated fault hypotheses")
    verification: List[VerificationOutcome] = Field(default_factory=list, description="Verification attempts and outcomes")
    candidate_probes: List[DiagnosticProbe] = Field(default_factory=list, description="All candidate diagnostic probes evaluated during planning")
    executed_probes: List[ProbeResult] = Field(default_factory=list, description="Diagnostic probes executed during adaptive investigation")
    investigation_history: List[DiagnosticDecisionRecord] = Field(default_factory=list, description="Step-by-step decision records explaining planner choices and stopping conditions")
    stopping_reason: Optional[str] = Field(None, description="Explanation of why the adaptive diagnostic loop terminated")
    summary: str = Field(..., description="Executive diagnostic summary")
    recommendations: List[str] = Field(default_factory=list, description="Prioritized recommendations")
    abstention_reason: Optional[str] = Field(None, description="Abstention notice if evidence is insufficient")
    error_message: Optional[str] = Field(None, description="Sanitized error explanation if run failed")
    started_at: datetime = Field(..., description="UTC start timestamp")
    completed_at: datetime = Field(..., description="UTC completion timestamp")
    duration_ms: float = Field(..., ge=0.0, description="Total execution duration in milliseconds")
