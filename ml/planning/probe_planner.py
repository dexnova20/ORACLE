"""Adaptive diagnostic probe planner for ORACLE diagnostic intelligence."""

import math
import os
import sys
from typing import Dict, List, Optional, Set, Tuple

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from oracle.schemas.diagnostics import (
    DiagnosticDecisionRecord,
    DiagnosticEvidenceRecord,
    DiagnosticProbe,
    DiagnosticSystemMap,
    FaultHypothesis,
    ProbeResult,
)
from ml.taxonomy.fault_taxonomy import FaultCategory

# Approved mapping for dynamic workload profile IDs
DYNAMIC_PROFILE_MAPPING: Dict[str, str] = {
    "isolated_runtime_env_audit": "benchmark-env-audit",
    "isolated_db_socket_probe": "benchmark-db-probe",
    "isolated_contract_check": "benchmark-contract-check",
    "isolated_transform_test": "benchmark-transform-test",
}


def calculate_shannon_entropy(probabilities: List[float]) -> float:
    """Calculate Shannon entropy H(p) = -sum(p_i * log2(p_i)) over a valid distribution.

    Raises ValueError if probabilities do not sum to approximately 1.0 or contain values < 0.
    """
    if not probabilities:
        return 0.0

    total = sum(probabilities)
    if not (0.98 <= total <= 1.02):
        raise ValueError(
            f"Shannon entropy requires a valid probability distribution summing to 1.0 (got sum={total:.4f})."
        )

    entropy = 0.0
    for p in probabilities:
        if p < 0.0:
            raise ValueError(f"Probabilities must be non-negative (got {p}).")
        if p > 0.0:
            entropy -= p * math.log2(p)
    return max(0.0, entropy)


def calculate_expected_information_gain(
    prior_probabilities: List[float],
    conditional_probabilities_by_outcome: Dict[str, Tuple[float, List[float]]],
) -> float:
    """Calculate Expected Information Gain (EIG) = H(Prior) - E[H(Posterior)].

    Args:
        prior_probabilities: P(H_i), valid probability distribution summing to 1.0.
        conditional_probabilities_by_outcome: Mapping outcome_name -> (P(outcome), [P(H_i | outcome)])
            where outcome probabilities sum to 1.0 and each posterior sums to 1.0.
    """
    prior_entropy = calculate_shannon_entropy(prior_probabilities)

    expected_posterior_entropy = 0.0
    total_outcome_prob = sum(p_out for p_out, _ in conditional_probabilities_by_outcome.values())
    if not (0.98 <= total_outcome_prob <= 1.02):
        raise ValueError(
            f"Outcome probabilities must sum to 1.0 (got {total_outcome_prob:.4f})."
        )

    for outcome, (p_outcome, posterior) in conditional_probabilities_by_outcome.items():
        if p_outcome > 0.0:
            h_post = calculate_shannon_entropy(posterior)
            expected_posterior_entropy += p_outcome * h_post

    eig = prior_entropy - expected_posterior_entropy
    return max(0.0, eig)


class ProbePlannerConfig:
    """Configuration parameters for adaptive probe selection."""

    def __init__(
        self,
        max_iterations: int = 5,
        cost_weight: float = 0.5,
        static_probe_base_cost: float = 1.0,
        manifest_probe_base_cost: float = 2.0,
        dynamic_probe_base_cost: float = 10.0,
    ) -> None:
        self.max_iterations = max_iterations
        self.cost_weight = cost_weight
        self.static_probe_base_cost = static_probe_base_cost
        self.manifest_probe_base_cost = manifest_probe_base_cost
        self.dynamic_probe_base_cost = dynamic_probe_base_cost


class ProbePlanner:
    """Generates, scores, and selects diagnostic probes to reduce hypothesis uncertainty."""

    def __init__(self, config: Optional[ProbePlannerConfig] = None) -> None:
        self.config = config or ProbePlannerConfig()

    def generate_candidate_probes(
        self,
        hypotheses: List[FaultHypothesis],
        evidence: List[DiagnosticEvidenceRecord],
        system_map: DiagnosticSystemMap,
        allow_dynamic: bool = False,
        preflight_available: bool = False,
        executed_probe_ids: Optional[Set[str]] = None,
    ) -> List[DiagnosticProbe]:
        """Generate candidate probes addressing current hypotheses and system structure."""
        executed = executed_probe_ids or set()
        candidates: List[DiagnosticProbe] = []
        probe_seq = 1

        # Map existing evidence by type and source
        evid_by_component: Dict[str, List[DiagnosticEvidenceRecord]] = {}
        for ev in evidence:
            evid_by_component.setdefault(ev.source_component, []).append(ev)

        # 1. Probes for Syntax Defect Hypotheses (group by target component)
        syntax_components: Dict[str, List[str]] = {}
        for h in hypotheses:
            if h.category == FaultCategory.RUNTIME_EXCEPTION and "Syntax" in h.category_title or any(
                "syntax" in eid.lower() for eid in h.supporting_evidence_ids
            ):
                comp = f"file:{h.affected_component}"
                syntax_components.setdefault(comp, []).append(h.hypothesis_id)

        for comp, hids in syntax_components.items():
            clean_name = comp.replace("file:", "").replace("/", "_").replace(".", "_")
            pid = f"PROBE-SYNTAX-{clean_name}"
            if pid not in executed:
                candidates.append(
                    DiagnosticProbe(
                        probe_id=pid,
                        probe_type="static_ast_syntax_check",
                        target_component=comp,
                        prerequisites=["file_accessible"],
                        target_hypothesis_ids=hids,
                        expected_outcomes=[
                            "syntax_error_reproduced",
                            "syntax_valid_unreproduced",
                        ],
                        estimated_cost=self.config.static_probe_base_cost,
                        cost_label="heuristic_estimate",
                        safety_classification="safe_static_analysis",
                        requires_dynamic=False,
                        availability_status="available",
                        selection_reason=f"Verify static AST syntax violation in '{comp}' to distinguish hypotheses {hids}.",
                    )
                )

        # 2. Probes for Internal Dependency Import Failure Hypotheses (group by component)
        import_components: Dict[str, List[str]] = {}
        for h in hypotheses:
            if h.category == FaultCategory.DEPENDENCY_IMPORT_FAILURE and any(
                "import" in eid.lower() for eid in h.supporting_evidence_ids
            ):
                comp = f"file:{h.affected_component}"
                import_components.setdefault(comp, []).append(h.hypothesis_id)

        for comp, hids in import_components.items():
            clean_name = comp.replace("file:", "").replace("/", "_").replace(".", "_")
            pid = f"PROBE-IMPORT-{clean_name}"
            if pid not in executed:
                candidates.append(
                    DiagnosticProbe(
                        probe_id=pid,
                        probe_type="static_import_resolution_check",
                        target_component=comp,
                        prerequisites=["filesystem_enumerated"],
                        target_hypothesis_ids=hids,
                        expected_outcomes=[
                            "missing_module_confirmed",
                            "misconfigured_source_root_detected",
                        ],
                        estimated_cost=self.config.static_probe_base_cost,
                        cost_label="heuristic_estimate",
                        safety_classification="safe_static_analysis",
                        requires_dynamic=False,
                        availability_status="available",
                        selection_reason=f"Verify internal import resolution in '{comp}' to distinguish hypotheses {hids}.",
                    )
                )

        # 3. Probes for External Undeclared Dependency Hypotheses
        manifest_components: Dict[str, List[str]] = {}
        for h in hypotheses:
            if h.category == FaultCategory.DEPENDENCY_IMPORT_FAILURE and any(
                "extdep" in eid.lower() for eid in h.supporting_evidence_ids
            ):
                manifest_components.setdefault(h.affected_component, []).append(h.hypothesis_id)

        for comp, hids in manifest_components.items():
            clean_name = comp.replace("/", "_").replace(".", "_").replace(" ", "").replace(",", "_")
            pid = f"PROBE-MANIFEST-{clean_name}"
            if pid not in executed:
                candidates.append(
                    DiagnosticProbe(
                        probe_id=pid,
                        probe_type="static_manifest_audit",
                        target_component=comp,
                        prerequisites=["manifest_file_accessible"],
                        target_hypothesis_ids=hids,
                        expected_outcomes=[
                            "undeclared_in_manifest_confirmed",
                            "optional_dependency_detected",
                        ],
                        estimated_cost=self.config.manifest_probe_base_cost,
                        cost_label="heuristic_estimate",
                        safety_classification="safe_static_analysis",
                        requires_dynamic=False,
                        availability_status="available",
                        selection_reason=f"Audit manifest files for undeclared external packages: {comp}.",
                    )
                )

        # 4. Probes for Dynamic Scenarios (Config, Socket, Contract, Transform)
        for h in hypotheses:
            probe_type: Optional[str] = None
            if h.category == FaultCategory.CONFIG_MISSING_OR_INVALID:
                probe_type = "isolated_runtime_env_audit"
            elif h.category == FaultCategory.DATABASE_CONNECTIVITY_SCHEMA:
                probe_type = "isolated_db_socket_probe"
            elif h.category == FaultCategory.IO_CONTRACT_VIOLATION:
                probe_type = "isolated_contract_check"
            elif h.category == FaultCategory.DATA_VALIDATION_TRANSFORMATION:
                probe_type = "isolated_transform_test"

            if probe_type:
                pid = f"PROBE-DYN-{h.hypothesis_id}"
                if pid not in executed:
                    # Check safety gating
                    if not allow_dynamic:
                        avail = "unauthorized"
                        rej = "Dynamic execution not authorized by caller (allow_dynamic=False)."
                    elif not preflight_available:
                        avail = "unavailable_no_docker"
                        rej = (
                            "Host container runtime unavailable. Host execution fallback is strictly "
                            "prohibited to protect system security."
                        )
                    else:
                        avail = "available"
                        rej = None

                    candidates.append(
                        DiagnosticProbe(
                            probe_id=pid,
                            probe_type=probe_type,
                            target_component=h.affected_component,
                            prerequisites=["container_runtime_available", "allow_dynamic_authorized"],
                            target_hypothesis_ids=[h.hypothesis_id],
                            expected_outcomes=["workload_exit_0_success", "workload_exit_nonzero_failure"],
                            estimated_cost=self.config.dynamic_probe_base_cost,
                            cost_label="heuristic_estimate",
                            safety_classification="sandboxed_container_execution",
                            requires_dynamic=True,
                            availability_status=avail,
                            selection_reason=f"Execute approved workload profile for {h.category.value}.",
                            rejection_reason=rej,
                        )
                    )

        # 5. Dependency-Aware Downstream Probes
        # Check system map for downstream components importing suspected faulty components
        faulty_identifiers: Set[str] = set()
        for h in hypotheses:
            if h.verification_status in ("verified", "supported", "partially_verified", "candidate"):
                comp_clean = h.affected_component.replace("file:", "").replace("module:", "").strip()
                faulty_identifiers.add(comp_clean)
                faulty_identifiers.add(f"file:{comp_clean}")
                faulty_identifiers.add(f"module:{comp_clean}")
                if comp_clean.endswith(".py"):
                    mod_name = comp_clean[:-3]
                    faulty_identifiers.add(mod_name)
                    faulty_identifiers.add(f"module:{mod_name}")
                else:
                    for ext in (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs", ".java"):
                        if comp_clean.endswith(ext):
                            mod_name = comp_clean[: -len(ext)]
                            faulty_identifiers.add(mod_name)
                            faulty_identifiers.add(f"module:{mod_name}")
                            break
                    faulty_identifiers.add(f"{comp_clean}.py")
                    faulty_identifiers.add(f"file:{comp_clean}.py")

        for edge in system_map.edges:
            target_clean = edge.target_component_id.replace("file:", "").replace("module:", "").strip()
            if edge.target_component_id in faulty_identifiers or target_clean in faulty_identifiers:
                downstream_id = edge.source_component_id
                clean_ds = downstream_id.replace(":", "_").replace("/", "_").replace(".", "_")
                pid = f"PROBE-DOWNSTREAM-{clean_ds}"
                if pid not in executed:
                    candidates.append(
                        DiagnosticProbe(
                            probe_id=pid,
                            probe_type="downstream_independent_check",
                            target_component=downstream_id,
                            prerequisites=["file_accessible"],
                            target_hypothesis_ids=[
                                h.hypothesis_id
                                for h in hypotheses
                                if h.affected_component in faulty_identifiers
                                or f"file:{h.affected_component}" in faulty_identifiers
                            ],
                            expected_outcomes=[
                                "downstream_independent_syntax_valid",
                                "downstream_syntax_faulty",
                            ],
                            estimated_cost=self.config.static_probe_base_cost,
                            cost_label="heuristic_estimate",
                            safety_classification="safe_static_analysis",
                            requires_dynamic=False,
                            availability_status="available",
                            selection_reason=(
                                f"Downstream component '{downstream_id}' depends on suspected fault in "
                                f"'{edge.target_component_id}'. Perform independent static check to determine if "
                                f"it is independently healthy or structurally broken."
                            ),
                        )
                    )

        return candidates

    def calculate_discrimination_heuristic(
        self,
        probe: DiagnosticProbe,
        hypotheses: List[FaultHypothesis],
    ) -> float:
        """Calculate a deterministic discrimination score for a candidate probe.

        Used when empirical outcome probabilities are unavailable. Explicitly represents
        how effectively the probe tests and partitions the competing hypotheses.
        """
        if not hypotheses:
            return 0.0

        target_set = set(probe.target_hypothesis_ids)
        if not target_set:
            return 0.1

        # Sum relative ranking scores of targeted hypotheses normalized by total
        targeted_score_sum = sum(h.relative_ranking_score for h in hypotheses if h.hypothesis_id in target_set)
        total_score_sum = sum(h.relative_ranking_score for h in hypotheses) or 1.0

        relevance_ratio = targeted_score_sum / total_score_sum
        # Higher score if it addresses leading hypotheses
        return max(0.1, round(relevance_ratio * 10.0, 2))

    def select_next_probe(
        self,
        candidate_probes: List[DiagnosticProbe],
        hypotheses: List[FaultHypothesis],
        iteration: int,
    ) -> Tuple[Optional[DiagnosticProbe], DiagnosticDecisionRecord]:
        """Select the next useful diagnostic probe based on discrimination score, safety, and cost."""
        if not hypotheses:
            return None, DiagnosticDecisionRecord(
                iteration=iteration,
                decision_type="stop_investigation",
                selected_probe_id=None,
                rationale="Zero fault hypotheses generated. Investigation halted on clean project.",
                candidates_considered_count=0,
                remaining_uncertainty=None,
                stopping_reason="sufficient_evidence_verified",
            )

        # Check deliberate abstention
        if len(hypotheses) == 1 and hypotheses[0].category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
            return None, DiagnosticDecisionRecord(
                iteration=iteration,
                decision_type="deliberate_abstention",
                selected_probe_id=None,
                rationale=f"Deliberate abstention: {hypotheses[0].abstention_reason}",
                candidates_considered_count=len(candidate_probes),
                remaining_uncertainty=hypotheses[0].abstention_reason,
                stopping_reason="deliberate_abstention",
            )

        # Check if iteration budget exhausted
        if iteration > self.config.max_iterations:
            return None, DiagnosticDecisionRecord(
                iteration=iteration,
                decision_type="stop_investigation",
                selected_probe_id=None,
                rationale=f"Investigation reached maximum iteration budget ({self.config.max_iterations}).",
                candidates_considered_count=len(candidate_probes),
                remaining_uncertainty="Unverified hypotheses remain due to iteration budget limit.",
                stopping_reason="budget_exhausted",
            )

        # Filter candidate probes
        available_probes = [p for p in candidate_probes if p.availability_status == "available"]
        unavailable_probes = [p for p in candidate_probes if p.availability_status != "available"]

        if not available_probes:
            # Check why no available probes remain
            if unavailable_probes:
                unavail_reasons = {p.rejection_reason for p in unavailable_probes if p.rejection_reason}
                reason_summary = "; ".join(unavail_reasons)
                return None, DiagnosticDecisionRecord(
                    iteration=iteration,
                    decision_type="reject_unsafe_probe",
                    selected_probe_id=None,
                    rationale=f"All remaining candidate probes are unavailable: {reason_summary}.",
                    candidates_considered_count=len(candidate_probes),
                    remaining_uncertainty="Dynamic verification probes unavailable without host container runtime.",
                    stopping_reason="further_investigation_unsafe_or_unsupported",
                )

            # Check if existing leading hypotheses are already verified or sufficiently supported
            top_hypo = hypotheses[0] if hypotheses else None
            if all(h.verification_status == "verified" for h in hypotheses) or (
                top_hypo
                and top_hypo.verification_status in ("verified", "partially_verified")
                and top_hypo.relative_ranking_score >= 60.0
            ):
                return None, DiagnosticDecisionRecord(
                    iteration=iteration,
                    decision_type="stop_investigation",
                    selected_probe_id=None,
                    rationale=(
                        f"Leading fault hypothesis '{top_hypo.hypothesis_id}' ({top_hypo.category.value}) "
                        f"has been independently verified/supported with relative score {top_hypo.relative_ranking_score:.1f}."
                    ),
                    candidates_considered_count=0,
                    remaining_uncertainty=None,
                    stopping_reason="sufficient_evidence_verified",
                )

            return None, DiagnosticDecisionRecord(
                iteration=iteration,
                decision_type="stop_investigation",
                selected_probe_id=None,
                rationale="No further informative probes available for remaining hypotheses.",
                candidates_considered_count=0,
                remaining_uncertainty="Remaining hypotheses cannot be further differentiated with available adapters.",
                stopping_reason="no_useful_probe_available",
            )

        # Score available probes by utility = DiscriminationHeuristic / (Cost ** cost_weight)
        scored_probes: List[Tuple[float, DiagnosticProbe, str]] = []
        for p in available_probes:
            discrim_score = self.calculate_discrimination_heuristic(p, hypotheses)
            cost_penalty = max(0.5, p.estimated_cost ** self.config.cost_weight)
            utility = round(discrim_score / cost_penalty, 3)

            rationale = (
                f"Utility {utility:.2f} (Discrimination heuristic: {discrim_score:.2f}, "
                f"estimated cost: {p.estimated_cost:.1f} [{p.cost_label}]). "
                f"Targeting hypotheses: {', '.join(p.target_hypothesis_ids)}."
            )
            scored_probes.append((utility, p, rationale))

        # Select the highest utility probe
        scored_probes.sort(key=lambda x: x[0], reverse=True)
        best_utility, best_probe, best_rationale = scored_probes[0]

        decision = DiagnosticDecisionRecord(
            iteration=iteration,
            decision_type="select_probe",
            selected_probe_id=best_probe.probe_id,
            rationale=f"Selected probe '{best_probe.probe_id}' ({best_probe.probe_type}): {best_rationale}",
            candidates_considered_count=len(candidate_probes),
            remaining_uncertainty=f"Testing targeted hypotheses {best_probe.target_hypothesis_ids}",
            stopping_reason=None,
        )

        return best_probe, decision
