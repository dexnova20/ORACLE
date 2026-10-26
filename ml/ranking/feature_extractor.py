"""Leak-free feature extraction for machine learning diagnostic ranking models.

Strictly extracts observable evidence signals, graph structural metrics, and
telemetry observations without referencing ground truth labels, scenario IDs, or project names.
"""

from typing import Any, Dict, List, Optional, Set
import numpy as np

from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.schemas.diagnostics import (
    DiagnosticEvidenceRecord,
    DiagnosticSystemMap,
    FaultHypothesis,
)

# Number of features in the dense feature vector
NUM_FEATURES = 24

# Stable category-to-index mapping for feature encoding
CATEGORY_INDICES: Dict[FaultCategory, int] = {
    FaultCategory.CONFIG_MISSING_OR_INVALID: 0,
    FaultCategory.DEPENDENCY_IMPORT_FAILURE: 1,
    FaultCategory.IO_CONTRACT_VIOLATION: 2,
    FaultCategory.RUNTIME_EXCEPTION: 3,
    FaultCategory.DATA_VALIDATION_TRANSFORMATION: 4,
    FaultCategory.API_COMMUNICATION_FAILURE: 5,
    FaultCategory.DATABASE_CONNECTIVITY_SCHEMA: 6,
    FaultCategory.MODEL_LOADING_INFERENCE_FAILURE: 7,
    FaultCategory.PERFORMANCE_ANOMALY: 8,
    FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE: 9,
}

FEATURE_NAMES: List[str] = [
    "num_supporting_evidence",
    "num_direct_observations",
    "num_inferred_signals",
    "num_limited_context",
    "num_contradicting_evidence",
    "has_syntax_evidence",
    "has_unresolved_import",
    "has_undeclared_dependency",
    "has_runtime_telemetry",
    "telemetry_confidence_max",
    "is_verified",
    "is_partially_verified",
    "is_supported",
    "is_candidate",
    "is_contradicted",
    "is_insufficient_evidence",
    "num_assumptions",
    "num_alternative_explanations",
    "graph_node_count",
    "graph_edge_count",
    "graph_unresolved_edge_ratio",
    "category_index",
    "evidence_diversity_ratio",
    "affected_component_in_graph",
]


def extract_hypothesis_features(
    hypo: FaultHypothesis,
    evidence: List[DiagnosticEvidenceRecord],
    system_map: Optional[DiagnosticSystemMap] = None,
) -> np.ndarray:
    """Extract a dense numerical feature vector for a candidate FaultHypothesis.

    Guarantees:
    - Pure mathematical mapping.
    - Zero code execution.
    - Zero ground truth label leakage.
    - Deterministic output shape (NUM_FEATURES,).
    """
    evidence_by_id = {e.evidence_id: e for e in evidence}
    vec = np.zeros(NUM_FEATURES, dtype=np.float64)

    # 1. Evidence counts and reliabilities
    supporting_recs = [evidence_by_id[eid] for eid in hypo.supporting_evidence_ids if eid in evidence_by_id]
    vec[0] = float(len(supporting_recs))

    n_direct = sum(1 for r in supporting_recs if r.reliability == "direct_observation")
    n_inferred = sum(1 for r in supporting_recs if r.reliability == "inferred_signal")
    n_limited = sum(1 for r in supporting_recs if r.reliability == "limited_context")
    vec[1] = float(n_direct)
    vec[2] = float(n_inferred)
    vec[3] = float(n_limited)

    # 2. Contradiction count
    contradicting_recs = [evidence_by_id[cid] for cid in hypo.contradicting_evidence_ids if cid in evidence_by_id]
    vec[4] = float(len(contradicting_recs))

    # 3. Evidence type indicators
    ev_types = {r.evidence_type for r in supporting_recs}
    vec[5] = 1.0 if "syntax_error" in ev_types else 0.0
    vec[6] = 1.0 if "unresolved_import" in ev_types else 0.0
    vec[7] = 1.0 if "undeclared_external_dependency" in ev_types else 0.0
    vec[8] = 1.0 if "runtime_telemetry" in ev_types else 0.0

    # 4. Telemetry confidence
    telem_confs = [
        float(r.observed_data.get("confidence", 0.0))
        for r in supporting_recs
        if r.evidence_type == "runtime_telemetry"
    ]
    vec[9] = max(telem_confs) if telem_confs else 0.0

    # 5. Verification status one-hot
    vec[10] = 1.0 if hypo.verification_status == "verified" else 0.0
    vec[11] = 1.0 if hypo.verification_status == "partially_verified" else 0.0
    vec[12] = 1.0 if hypo.verification_status == "supported" else 0.0
    vec[13] = 1.0 if hypo.verification_status == "candidate" else 0.0
    vec[14] = 1.0 if hypo.verification_status == "contradicted" else 0.0
    vec[15] = 1.0 if hypo.verification_status == "insufficient_evidence" else 0.0

    # 6. Complexity indicators
    vec[16] = float(len(hypo.assumptions))
    vec[17] = float(len(hypo.alternative_explanations))

    # 7. System map structural metrics
    if system_map and system_map.total_components > 0:
        vec[18] = float(system_map.total_components)
        vec[19] = float(system_map.total_dependencies)
        unres = float(system_map.unresolved_dependency_count)
        total_deps = max(1.0, float(system_map.total_dependencies))
        vec[20] = unres / total_deps

        comp_ids = {c.id for c in system_map.components}
        target_cid = f"file:{hypo.affected_component}"
        vec[23] = 1.0 if (target_cid in comp_ids or hypo.affected_component in comp_ids) else 0.0
    else:
        vec[18] = 0.0
        vec[19] = 0.0
        vec[20] = 0.0
        vec[23] = 0.0

    # 8. Category index & evidence diversity
    cat_idx = CATEGORY_INDICES.get(hypo.category, 9)
    vec[21] = float(cat_idx)
    vec[22] = float(len(ev_types)) / max(1.0, float(len(supporting_recs)))

    return vec


def extract_feature_matrix(
    hypotheses: List[FaultHypothesis],
    evidence: List[DiagnosticEvidenceRecord],
    system_map: Optional[DiagnosticSystemMap] = None,
) -> np.ndarray:
    """Extract a 2D numpy array of shape (len(hypotheses), NUM_FEATURES)."""
    if not hypotheses:
        return np.empty((0, NUM_FEATURES), dtype=np.float64)

    rows = [
        extract_hypothesis_features(h, evidence, system_map)
        for h in hypotheses
    ]
    return np.vstack(rows)
