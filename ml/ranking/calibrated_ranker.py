"""Calibrated probabilistic ranking, multi-fault separation, and contradiction handling."""

import math
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from ml.taxonomy.fault_taxonomy import FAULT_TAXONOMY, FaultCategory
from oracle.schemas.diagnostics import (
    DiagnosticEvidenceRecord,
    DiagnosticSystemMap,
    FaultHypothesis,
)


def softmax(x: np.ndarray, temperature: float = 15.0) -> np.ndarray:
    """Compute softmax probabilities with temperature scaling."""
    if len(x) == 0:
        return np.array([])
    temp = max(1.0, temperature)
    scaled = (x - np.max(x)) / temp
    exp_scaled = np.exp(scaled)
    sum_exp = np.sum(exp_scaled)
    if sum_exp == 0.0 or np.isnan(sum_exp):
        return np.ones_like(x) / len(x)
    return exp_scaled / sum_exp


class CalibratedRanker:
    """Probabilistically calibrated hypothesis ranker with explicit contradiction handling and abstention."""

    def __init__(
        self,
        temperature: float = 20.0,
        abstention_threshold: float = 0.30,
        contradiction_penalty: float = 60.0,
    ) -> None:
        self.temperature = temperature
        self.abstention_threshold = abstention_threshold
        self.contradiction_penalty = contradiction_penalty

    def compute_calibrated_probabilities(
        self,
        hypotheses: List[FaultHypothesis],
        evidence: List[DiagnosticEvidenceRecord],
    ) -> List[Tuple[FaultHypothesis, float]]:
        """Compute well-calibrated posterior probabilities for hypotheses."""
        if not hypotheses:
            return []

        evidence_by_id = {e.evidence_id: e for e in evidence}
        raw_scores: List[float] = []

        for hypo in hypotheses:
            if hypo.category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
                raw_scores.append(0.0)
                continue

            score = hypo.relative_ranking_score or 50.0

            # Apply verification status weights
            if hypo.verification_status == "verified":
                score += 25.0
            elif hypo.verification_status == "partially_verified":
                score += 10.0
            elif hypo.verification_status == "contradicted":
                score -= self.contradiction_penalty
            elif hypo.verification_status == "insufficient_evidence":
                score -= 30.0

            # Contradicting evidence penalty
            n_contra = len([cid for cid in hypo.contradicting_evidence_ids if cid in evidence_by_id])
            score -= (n_contra * 25.0)

            # Prevent negative raw scores before softmax
            raw_scores.append(max(0.0, score))

        scores_arr = np.array(raw_scores, dtype=np.float64)
        probs = softmax(scores_arr, temperature=self.temperature)

        return list(zip(hypotheses, probs.tolist()))

    def rank_and_calibrate(
        self,
        hypotheses: List[FaultHypothesis],
        evidence: List[DiagnosticEvidenceRecord],
        system_map: Optional[DiagnosticSystemMap] = None,
    ) -> List[FaultHypothesis]:
        """Rank hypotheses, attach calibrated probabilities and rationale, and handle abstention."""
        if not hypotheses:
            return []

        # Check for deliberate abstention condition
        if len(hypotheses) == 1 and hypotheses[0].category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
            return hypotheses

        scored_pairs = self.compute_calibrated_probabilities(hypotheses, evidence)
        scored_pairs.sort(key=lambda pair: pair[1], reverse=True)

        max_prob = scored_pairs[0][1] if scored_pairs else 0.0
        should_abstain = max_prob < self.abstention_threshold

        ranked_results: List[FaultHypothesis] = []
        for hypo, prob in scored_pairs:
            calibrated_pct = round(prob * 100.0, 1)

            # Determine confidence level calibrated to probability
            if hypo.verification_status == "contradicted":
                conf_level = "refuted"
            elif prob >= 0.70:
                conf_level = "high"
            elif prob >= 0.40:
                conf_level = "medium"
            else:
                conf_level = "low"

            status = hypo.verification_status
            if should_abstain and status not in ("verified", "contradicted"):
                status = "insufficient_evidence"

            rationale = (
                f"Calibrated probability: {calibrated_pct}% "
                f"(verification_status={hypo.verification_status}, "
                f"supporting_evidence={len(hypo.supporting_evidence_ids)}, "
                f"contradictions={len(hypo.contradicting_evidence_ids)})."
            )
            if hypo.verification_status == "contradicted":
                rationale += " Hypothesis refuted by negative diagnostic probe finding."

            ranked_results.append(
                hypo.model_copy(
                    update={
                        "relative_ranking_score": calibrated_pct,
                        "confidence_level": conf_level,
                        "verification_status": status,
                        "score_rationale": rationale,
                    }
                )
            )

        return ranked_results

    def separate_multi_faults(
        self,
        ranked_hypotheses: List[FaultHypothesis],
        top_k_per_component: int = 1,
    ) -> List[FaultHypothesis]:
        """Group hypotheses by affected component to support distinct simultaneous multi-fault detection."""
        by_comp: Dict[str, List[FaultHypothesis]] = {}
        for h in ranked_hypotheses:
            if h.verification_status != "contradicted":
                by_comp.setdefault(h.affected_component, []).append(h)

        multi_fault_leaders: List[FaultHypothesis] = []
        for comp, hypos in by_comp.items():
            sorted_hypos = sorted(hypos, key=lambda x: x.relative_ranking_score, reverse=True)
            multi_fault_leaders.extend(sorted_hypos[:top_k_per_component])

        multi_fault_leaders.sort(key=lambda x: x.relative_ranking_score, reverse=True)
        return multi_fault_leaders
