"""Automated tests verifying leak-free invariant of ML feature extraction.

Asserts that feature extraction strictly operates on observable diagnostic signals
without leaking scenario IDs, repository names, target ground-truth labels, or post-verification outcomes.
"""

import numpy as np
import pytest

from ml.ranking.feature_extractor import NUM_FEATURES, FEATURE_NAMES, extract_hypothesis_features, extract_feature_matrix
from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.schemas.diagnostics import (
    DiagnosticComponent,
    DiagnosticEvidenceRecord,
    DiagnosticSystemMap,
    FaultHypothesis,
)


def _make_dummy_data():
    evidence = [
        DiagnosticEvidenceRecord(
            evidence_id="EVID-001",
            evidence_type="syntax_error",
            source_component="file:app/main.py",
            extraction_method="python_ast",
            location="app/main.py:12",
            observed_data={"error": "SyntaxError"},
            reliability="direct_observation",
        ),
        DiagnosticEvidenceRecord(
            evidence_id="EVID-002",
            evidence_type="runtime_telemetry",
            source_component="file:app/db.py",
            extraction_method="telemetry_analyzer",
            location="app/db.py:45",
            observed_data={"confidence": 0.92, "summary": "DB error"},
            reliability="direct_observation",
        ),
    ]

    hypo = FaultHypothesis(
        hypothesis_id="HYPO-001",
        category=FaultCategory.DATABASE_CONNECTIVITY_SCHEMA,
        category_title="Database Connectivity & Schema",
        affected_component="app/db.py",
        supporting_evidence_ids=["EVID-002"],
        contradicting_evidence_ids=[],
        assumptions=["DB is unreachable"],
        alternative_explanations=["Network timeout"],
        confidence_level="high",
        relative_ranking_score=92.0,
        score_rationale="Observed DB connection failure",
        verification_status="supported",
    )

    system_map = DiagnosticSystemMap(
        components=[
            DiagnosticComponent(id="file:app/main.py", name="app/main.py", component_type="source_file", status="defective"),
            DiagnosticComponent(id="file:app/db.py", name="app/db.py", component_type="source_file", status="healthy"),
        ],
        dependencies=[],
        total_components=2,
        total_dependencies=1,
        unresolved_dependency_count=0,
    )

    return hypo, evidence, system_map


def test_feature_vector_shape_and_names():
    """Verify feature vector length, name alignment, and dimensionality invariants."""
    assert len(FEATURE_NAMES) == NUM_FEATURES
    assert NUM_FEATURES == 24

    hypo, evidence, system_map = _make_dummy_data()
    vec = extract_hypothesis_features(hypo, evidence, system_map)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (24,)
    assert not np.isnan(vec).any()
    assert not np.isinf(vec).any()


def test_feature_invariance_to_scenario_identifiers():
    """Verify feature representation is strictly invariant to hypothesis ID, external names, and metadata."""
    hypo, evidence, system_map = _make_dummy_data()

    vec_base = extract_hypothesis_features(hypo, evidence, system_map)

    # Rename hypothesis ID
    hypo_renamed = hypo.model_copy(update={"hypothesis_id": "HYPO-DIFFERENT-999"})
    vec_renamed = extract_hypothesis_features(hypo_renamed, evidence, system_map)

    assert np.array_equal(vec_base, vec_renamed), "Hypothesis ID must not affect feature representation"

    # Rename score rationale
    hypo_mutated_rationale = hypo.model_copy(update={"score_rationale": "Completely different rationale text"})
    vec_mutated = extract_hypothesis_features(hypo_mutated_rationale, evidence, system_map)

    assert np.array_equal(vec_base, vec_mutated), "Text rationale must not affect feature representation"


def test_feature_extraction_without_system_map():
    """Verify robust extraction when system map is missing or empty."""
    hypo, evidence, _ = _make_dummy_data()
    vec_none = extract_hypothesis_features(hypo, evidence, None)

    assert vec_none.shape == (24,)
    assert not np.isnan(vec_none).any()
    assert vec_none[18] == 0.0  # graph_node_count
    assert vec_none[19] == 0.0  # graph_edge_count
    assert vec_none[20] == 0.0  # graph_unresolved_edge_ratio
    assert vec_none[23] == 0.0  # affected_component_in_graph


def test_feature_matrix_extraction():
    """Verify batch 2D feature matrix extraction."""
    hypo, evidence, system_map = _make_dummy_data()
    hypo2 = hypo.model_copy(update={"hypothesis_id": "HYPO-002", "category": FaultCategory.RUNTIME_EXCEPTION})

    mat = extract_feature_matrix([hypo, hypo2], evidence, system_map)
    assert isinstance(mat, np.ndarray)
    assert mat.shape == (2, 24)

    empty_mat = extract_feature_matrix([], evidence, system_map)
    assert empty_mat.shape == (0, 24)


def test_zero_ground_truth_leakage():
    """Verify that feature extractor module contains zero references to ground-truth labels."""
    import inspect
    import ml.ranking.feature_extractor as fe_mod

    source = inspect.getsource(fe_mod)

    # Assert no references to ground truth, benchmark scenario identifiers, or answers
    forbidden_terms = [
        "ground_truth",
        "expected_category",
        "expected_component",
        "is_healthy_control",
        "is_abstention_case",
        "scenario_id",
        "GEN-",
        "BENCH-",
    ]
    for term in forbidden_terms:
        assert term not in source, f"Feature extractor contains forbidden ground truth reference: {term}"
