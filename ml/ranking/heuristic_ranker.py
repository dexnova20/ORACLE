"""Transparent, deterministic hypothesis ranking baseline for ORACLE diagnostic intelligence."""

import os
import sys
from typing import Dict, List, Optional, Set

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from oracle.schemas.diagnostics import (
    DiagnosticEvidenceRecord,
    DiagnosticSystemMap,
    FaultHypothesis,
)
from ml.taxonomy.fault_taxonomy import FaultCategory


class HeuristicRankerConfig:
    """Configurable scoring weights for deterministic relative hypothesis ranking."""

    def __init__(
        self,
        direct_observation_weight: float = 35.0,
        inferred_signal_weight: float = 15.0,
        limited_context_weight: float = 5.0,
        independent_corroboration_bonus: float = 15.0,
        verified_bonus: float = 35.0,
        supported_bonus: float = 15.0,
        candidate_bonus: float = 5.0,
        contradiction_penalty: float = 40.0,
        uncertainty_penalty: float = 10.0,
    ) -> None:
        self.direct_observation_weight = direct_observation_weight
        self.inferred_signal_weight = inferred_signal_weight
        self.limited_context_weight = limited_context_weight
        self.independent_corroboration_bonus = independent_corroboration_bonus
        self.verified_bonus = verified_bonus
        self.supported_bonus = supported_bonus
        self.candidate_bonus = candidate_bonus
        self.contradiction_penalty = contradiction_penalty
        self.uncertainty_penalty = uncertainty_penalty


def rank_hypotheses(
    hypotheses: List[FaultHypothesis],
    evidence: List[DiagnosticEvidenceRecord],
    system_map: Optional[DiagnosticSystemMap] = None,
    config: Optional[HeuristicRankerConfig] = None,
) -> List[FaultHypothesis]:
    """Rank hypotheses using transparent, deterministic scoring.

    Important:
    - Scores are relative heuristic ranking metrics in [0.0, 100.0].
    - Scores are NOT calibrated probabilities.
    - If two competing hypotheses share identical supporting evidence,
      their scores remain identical (ambiguity is preserved).
    - If the evidence set is empty or indicates deliberate abstention,
      hypotheses are scored accordingly without manufactured confidence.
    """
    cfg = config or HeuristicRankerConfig()
    evidence_by_id: Dict[str, DiagnosticEvidenceRecord] = {e.evidence_id: e for e in evidence}

    ranked: List[FaultHypothesis] = []

    for hypo in hypotheses:
        # Deliberate abstention case
        if hypo.category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE:
            updated = hypo.model_copy(
                update={
                    "relative_ranking_score": 0.0,
                    "score_rationale": (
                        "Relative ranking score: 0.0/100 (Deliberate abstention: "
                        f"{hypo.abstention_reason or 'Insufficient observable evidence to support fault diagnosis'}). "
                        "Note: Relative heuristic score, NOT a calibrated probability."
                    ),
                    "confidence_level": "uncertain",
                    "verification_status": "insufficient_evidence",
                }
            )
            ranked.append(updated)
            continue

        raw_score = 0.0
        rationale_parts: List[str] = []

        # Deduplicate evidence IDs while preserving input order of first appearance
        seen_supporting: Set[str] = set()
        deduped_supporting: List[str] = []
        for eid in hypo.supporting_evidence_ids:
            if eid not in seen_supporting:
                seen_supporting.add(eid)
                deduped_supporting.append(eid)

        seen_contradicting: Set[str] = set()
        deduped_contradicting: List[str] = []
        for cid in hypo.contradicting_evidence_ids:
            if cid not in seen_contradicting:
                seen_contradicting.add(cid)
                deduped_contradicting.append(cid)

        # 1. Base evidence weight (order-invariant and with diminishing returns for repeated signals)
        valid_records: List[DiagnosticEvidenceRecord] = []
        distinct_source_components: Set[str] = set()

        for eid in deduped_supporting:
            rec = evidence_by_id.get(eid)
            if not rec:
                # Dangling evidence reference penalty (applied once per unique dangling reference)
                raw_score -= 10.0
                rationale_parts.append(f"Dangling evidence reference '{eid}' (-10.0)")
            else:
                valid_records.append(rec)
                distinct_source_components.add(rec.source_component)

        # Group records by evidence_type for order-invariant scoring
        records_by_type: Dict[str, List[DiagnosticEvidenceRecord]] = {}
        for rec in valid_records:
            records_by_type.setdefault(rec.evidence_type, []).append(rec)

        def _reliability_priority(r: DiagnosticEvidenceRecord) -> int:
            if r.reliability == "direct_observation":
                return 3
            if r.reliability == "inferred_signal":
                return 2
            return 1

        for etype, group in sorted(records_by_type.items()):
            # Select the most reliable record of this type as the primary observation
            sorted_group = sorted(group, key=lambda r: (_reliability_priority(r), r.evidence_id), reverse=True)
            primary_rec = sorted_group[0]

            if primary_rec.reliability == "direct_observation":
                raw_score += cfg.direct_observation_weight
                rationale_parts.append(f"Direct observation '{primary_rec.evidence_id}' (+{cfg.direct_observation_weight})")
            elif primary_rec.reliability == "inferred_signal":
                raw_score += cfg.inferred_signal_weight
                rationale_parts.append(f"Inferred signal '{primary_rec.evidence_id}' (+{cfg.inferred_signal_weight})")
            else:
                raw_score += cfg.limited_context_weight
                rationale_parts.append(f"Limited context observation '{primary_rec.evidence_id}' (+{cfg.limited_context_weight})")

            # Subsequent observations of the identical category receive diminishing marginal weight
            for add_rec in sorted_group[1:]:
                raw_score += 5.0
                rationale_parts.append(f"Additional evidence '{add_rec.evidence_id}' (+5.0)")

        # 2. Independent corroboration across distinct source components
        if len(distinct_source_components) > 1:
            corrob_points = (len(distinct_source_components) - 1) * cfg.independent_corroboration_bonus
            raw_score += corrob_points
            rationale_parts.append(
                f"Independent corroboration across {len(distinct_source_components)} distinct components (+{corrob_points})"
            )

        # 3. Contradicting evidence penalty
        for cid in deduped_contradicting:
            rec = evidence_by_id.get(cid)
            if rec:
                raw_score -= cfg.contradiction_penalty
                rationale_parts.append(f"Contradicting evidence '{cid}' (-{cfg.contradiction_penalty})")

        # 4. Verification outcome bonus
        vstatus = hypo.verification_status
        if vstatus == "verified":
            raw_score += cfg.verified_bonus
            rationale_parts.append(f"Independently verified (+{cfg.verified_bonus})")
        elif vstatus in ("supported", "partially_verified"):
            raw_score += cfg.supported_bonus
            rationale_parts.append(f"Empirically supported (+{cfg.supported_bonus})")
        elif vstatus == "candidate":
            raw_score += cfg.candidate_bonus
            rationale_parts.append(f"Candidate hypothesis (+{cfg.candidate_bonus})")
        elif vstatus == "contradicted":
            raw_score -= 50.0
            rationale_parts.append("Refuted by verification check (-50.0)")
        elif vstatus == "blocked":
            raw_score -= cfg.uncertainty_penalty
            rationale_parts.append(f"Blocked by upstream component dependency (-{cfg.uncertainty_penalty})")

        # 5. Uncertainty penalty
        if hypo.uncertainty_reason:
            raw_score -= cfg.uncertainty_penalty
            rationale_parts.append(f"Remaining uncertainty (-{cfg.uncertainty_penalty})")

        # Bound score to [0.0, 100.0]
        final_score = max(0.0, min(100.0, round(raw_score, 1)))

        # Derive confidence level from relative score
        if final_score >= 70.0:
            clevel = "high"
        elif final_score >= 40.0:
            clevel = "medium"
        elif final_score > 0.0:
            clevel = "low"
        else:
            clevel = "uncertain"

        rationale_str = (
            f"Relative ranking score: {final_score}/100. Breakdown: {'; '.join(rationale_parts)}. "
            "Note: This is a relative heuristic ranking score, NOT a calibrated probability."
        )

        updated = hypo.model_copy(
            update={
                "relative_ranking_score": final_score,
                "score_rationale": rationale_str,
                "confidence_level": clevel,
            }
        )
        ranked.append(updated)

    # Sort descending by relative ranking score; preserve input order on ties
    return sorted(ranked, key=lambda h: h.relative_ranking_score, reverse=True)
