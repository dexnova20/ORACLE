"""Empirical evaluation and comparative benchmarking of adaptive vs fixed probe policies.

Quantifies Shannon entropy reduction (Delta H), probe efficiency (Delta H / Cost),
and investigation cost across adaptive, static-first, dynamic-first, and random policies.
"""

from dataclasses import dataclass
import math
import random
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ml.planning.probe_planner import (
    ProbePlanner,
    ProbePlannerConfig,
    calculate_shannon_entropy,
)
from ml.ranking.calibrated_ranker import softmax
from oracle.schemas.diagnostics import (
    DiagnosticEvidenceRecord,
    DiagnosticProbe,
    DiagnosticSystemMap,
    FaultHypothesis,
    ProbeResult,
)


@dataclass
class PolicyEvaluationResult:
    """Summary metrics of a probe planning strategy across evaluation scenarios."""

    policy_name: str
    total_probes_executed: int
    mean_probes_per_scenario: float
    mean_entropy_reduction: float
    mean_cost_incurred: float
    probe_efficiency: float  # Entropy reduction per unit cost
    unnecessary_probes_avoided: int
    convergence_rate: float  # Fraction of scenarios where true cause was verified


def simulate_probe_outcome(
    probe: DiagnosticProbe,
    ground_truth_category: str,
    ground_truth_component: str,
) -> str:
    """Simulate ground truth probe outcome for benchmarking."""
    target_comp = probe.target_component.replace("file:", "").strip()
    clean_gt_comp = ground_truth_component.replace("file:", "").strip()

    if target_comp == clean_gt_comp:
        return "confirmed"
    elif probe.probe_type == "static_ast_probe" and clean_gt_comp in target_comp:
        return "confirmed"
    elif probe.probe_type == "static_manifest_audit" and "pkg:" in target_comp:
        return "confirmed"
    return "refuted"


def evaluate_probe_policies(
    scenarios: List[Dict[str, Any]],
    random_seed: int = 42,
) -> Dict[str, PolicyEvaluationResult]:
    """Evaluate adaptive vs fixed sequence probe strategies across benchmark scenarios.

    Compares:
    1. adaptive_information_gain: ORACLE adaptive planner selecting max(EIG/Cost).
    2. fixed_static_first: Static AST probes, then manifest audits, then dynamic probes.
    3. fixed_dynamic_first: Dynamic probes first, then static checks.
    4. random_selection: Random probe ordering.
    """
    rng = random.Random(random_seed)
    policies = ["adaptive_information_gain", "fixed_static_first", "fixed_dynamic_first", "random_selection"]

    stats: Dict[str, Dict[str, float]] = {
        p: {
            "probes": 0.0,
            "entropy_reduction": 0.0,
            "cost": 0.0,
            "converged": 0.0,
            "redundant_avoided": 0.0,
        }
        for p in policies
    }

    planner = ProbePlanner(ProbePlannerConfig(max_iterations=5))

    for sc in scenarios:
        initial_hypos: List[FaultHypothesis] = sc["hypotheses"]
        initial_evidence: List[DiagnosticEvidenceRecord] = sc["evidence"]
        system_map = sc.get("system_map", DiagnosticSystemMap())
        gt_category = sc.get("ground_truth_category", "")
        gt_component = sc.get("ground_truth_component", "")

        # Initial prior distribution and entropy
        scores = np.array([h.relative_ranking_score or 50.0 for h in initial_hypos], dtype=np.float64)
        priors = softmax(scores, temperature=15.0).tolist()
        try:
            h_initial = calculate_shannon_entropy(priors)
        except Exception:
            h_initial = 1.0

        all_candidate_probes = planner.generate_candidate_probes(
            hypotheses=initial_hypos,
            evidence=initial_evidence,
            system_map=system_map,
            allow_dynamic=True,
            preflight_available=True,
        )
        if not all_candidate_probes:
            continue

        for pol in policies:
            executed: List[ProbeResult] = []
            exec_ids: set = set()
            cur_hypos = list(initial_hypos)
            cum_cost = 0.0

            for step in range(5):
                unexec = [p for p in all_candidate_probes if p.probe_id not in exec_ids]
                if not unexec:
                    break

                # 1. Selection
                if pol == "adaptive_information_gain":
                    selected, decision = planner.select_next_probe(
                        candidate_probes=unexec,
                        hypotheses=cur_hypos,
                        iteration=step + 1,
                    )
                    if not selected or decision.decision_type == "stop":
                        stats[pol]["redundant_avoided"] += len(unexec)
                        break
                elif pol == "fixed_static_first":
                    # Static AST -> Manifest Audit -> Dynamic
                    unexec_sorted = sorted(
                        unexec,
                        key=lambda p: (0 if p.probe_type == "static_ast_probe" else (1 if p.probe_type == "static_manifest_audit" else 2)),
                    )
                    selected = unexec_sorted[0] if unexec_sorted else None
                    if not selected:
                        break
                elif pol == "fixed_dynamic_first":
                    unexec_sorted = sorted(
                        unexec,
                        key=lambda p: (0 if "dynamic" in p.probe_type or "socket" in p.probe_type else 1),
                    )
                    selected = unexec_sorted[0] if unexec_sorted else None
                    if not selected:
                        break
                else:  # random_selection
                    selected = rng.choice(unexec) if unexec else None
                    if not selected:
                        break

                # 2. Simulate outcome
                outcome = simulate_probe_outcome(selected, gt_category, gt_component)
                cost = selected.estimated_cost
                cum_cost += cost
                exec_ids.add(selected.probe_id)

                # Update hypothesis scores based on outcome
                updated_hypos = []
                for h in cur_hypos:
                    if h.hypothesis_id in selected.target_hypothesis_ids:
                        new_score = (h.relative_ranking_score or 50.0) + (35.0 if outcome == "confirmed" else -40.0)
                        status = "verified" if outcome == "confirmed" else "contradicted"
                        updated_hypos.append(h.model_copy(update={"relative_ranking_score": max(5.0, new_score), "verification_status": status}))
                    else:
                        updated_hypos.append(h)
                cur_hypos = updated_hypos

                # Stop early if verified true cause
                if any(h.verification_status == "verified" and h.affected_component == gt_component for h in cur_hypos):
                    stats[pol]["converged"] += 1.0
                    stats[pol]["redundant_avoided"] += (len(all_candidate_probes) - len(exec_ids))
                    break

            # Compute posterior entropy
            post_scores = np.array([h.relative_ranking_score or 50.0 for h in cur_hypos], dtype=np.float64)
            post_probs = softmax(post_scores, temperature=15.0).tolist()
            try:
                h_final = calculate_shannon_entropy(post_probs)
            except Exception:
                h_final = 0.0

            delta_h = max(0.0, h_initial - h_final)
            stats[pol]["probes"] += len(exec_ids)
            stats[pol]["entropy_reduction"] += delta_h
            stats[pol]["cost"] += cum_cost

    num_scenarios = max(1, len(scenarios))
    results: Dict[str, PolicyEvaluationResult] = {}

    for pol in policies:
        tot_probes = int(stats[pol]["probes"])
        mean_probes = round(stats[pol]["probes"] / num_scenarios, 2)
        mean_dh = round(stats[pol]["entropy_reduction"] / num_scenarios, 4)
        mean_cost = round(stats[pol]["cost"] / num_scenarios, 2)
        eff = round(mean_dh / max(0.1, mean_cost), 4)
        conv = round(stats[pol]["converged"] / num_scenarios, 3)
        avoided = int(stats[pol]["redundant_avoided"])

        results[pol] = PolicyEvaluationResult(
            policy_name=pol,
            total_probes_executed=tot_probes,
            mean_probes_per_scenario=mean_probes,
            mean_entropy_reduction=mean_dh,
            mean_cost_incurred=mean_cost,
            probe_efficiency=eff,
            unnecessary_probes_avoided=avoided,
            convergence_rate=conv,
        )

    return results
