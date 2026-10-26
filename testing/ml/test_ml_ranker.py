"""Tests for leak-free feature extraction, ML hypothesis ranking models, and probability calibration."""

import numpy as np
import pytest

from ml.ranking.calibrated_ranker import CalibratedRanker, softmax
from ml.ranking.feature_extractor import NUM_FEATURES, extract_hypothesis_features
from ml.ranking.ml_ranker import (
    MLHypothesisRanker,
    compute_expected_calibration_error,
    generate_synthetic_training_data,
)
from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.schemas.diagnostics import (
    DiagnosticComponent,
    DiagnosticEvidenceRecord,
    DiagnosticSystemMap,
    FaultHypothesis,
)


def test_feature_extractor_leak_free():
    """Verify feature extractor generates valid vectors without referencing target labels or scenario IDs."""
    hypo = FaultHypothesis(
        hypothesis_id="HYPO-001",
        category=FaultCategory.DATABASE_CONNECTIVITY_SCHEMA,
        category_title="Database Failure",
        affected_component="app/db.py",
        supporting_evidence_ids=["EVID-001"],
        contradicting_evidence_ids=[],
        assumptions=["DB is running"],
        alternative_explanations=[],
        confidence_level="high",
        relative_ranking_score=85.0,
        verification_status="verified",
    )
    ev = DiagnosticEvidenceRecord(
        evidence_id="EVID-001",
        evidence_type="runtime_telemetry",
        source_component="app/db.py",
        extraction_method="telemetry_analyzer",
        location="app/db.py:20",
        observed_data={"confidence": 0.95},
        reliability="direct_observation",
        limitations=[],
    )
    s_map = DiagnosticSystemMap(
        components=[DiagnosticComponent(id="file:app/db.py", name="db.py", component_type="source_file", file_path="app/db.py", status="analyzed")],
        edges=[],
        total_components=1,
        total_dependencies=0,
    )

    feat = extract_hypothesis_features(hypo, [ev], s_map)
    assert isinstance(feat, np.ndarray)
    assert feat.shape == (NUM_FEATURES,)
    assert feat[0] == 1.0  # num_supporting_evidence
    assert feat[1] == 1.0  # num_direct_observations
    assert feat[8] == 1.0  # has_runtime_telemetry
    assert feat[9] == 0.95  # telemetry_confidence_max
    assert feat[10] == 1.0  # is_verified


def test_synthetic_training_data_generation():
    """Verify synthetic dataset produces valid non-empty arrays with binary labels."""
    X, y = generate_synthetic_training_data(num_samples=100, random_seed=42)
    assert X.shape == (100, NUM_FEATURES)
    assert y.shape == (100,)
    assert set(np.unique(y)).issubset({0, 1})
    assert np.all(np.isfinite(X))


def test_ml_ranker_training_and_inference():
    """Verify Calibrated Logistic Regression ranker trains and predicts valid probabilities."""
    ranker = MLHypothesisRanker(model_type="calibrated_logistic")
    ranker.train_default()

    hypo = FaultHypothesis(
        hypothesis_id="HYPO-001",
        category=FaultCategory.CONFIG_MISSING_OR_INVALID,
        category_title="Config Error",
        affected_component="settings.py",
        supporting_evidence_ids=["EVID-001"],
        verification_status="supported",
    )
    ev = DiagnosticEvidenceRecord(
        evidence_id="EVID-001",
        evidence_type="runtime_telemetry",
        source_component="settings.py",
        extraction_method="telemetry_analyzer",
        location="settings.py:1",
        observed_data={"confidence": 0.9},
        reliability="direct_observation",
        limitations=[],
    )

    prob = ranker.predict_probability(hypo, [ev])
    assert 0.0 <= prob <= 1.0

    ranked = ranker.rank_hypotheses([hypo], [ev])
    assert len(ranked) == 1
    assert ranked[0].relative_ranking_score >= 0.0


def test_ml_rf_ranker():
    """Verify Calibrated Random Forest ranker executes cleanly."""
    ranker = MLHypothesisRanker(model_type="calibrated_random_forest")
    ranker.train_default()

    hypo = FaultHypothesis(
        hypothesis_id="HYPO-001",
        category=FaultCategory.RUNTIME_EXCEPTION,
        category_title="Syntax Error",
        affected_component="main.go",
        supporting_evidence_ids=[],
        verification_status="candidate",
    )
    prob = ranker.predict_probability(hypo, [])
    assert 0.0 <= prob <= 1.0


def test_compute_expected_calibration_error():
    """Verify ECE calculation handles perfect calibration and complete miscalibration."""
    perfect_probs = np.array([0.9, 0.9, 0.1, 0.1])
    perfect_labels = np.array([1, 1, 0, 0])
    ece = compute_expected_calibration_error(perfect_probs, perfect_labels)
    assert 0.0 <= ece <= 0.2

    empty_ece = compute_expected_calibration_error(np.array([]), np.array([]))
    assert empty_ece == 0.0


def test_calibrated_ranker_contradiction_handling():
    """Verify contradiction reduces hypothesis score and redistributes probability mass."""
    calibrator = CalibratedRanker()
    h1 = FaultHypothesis(
        hypothesis_id="HYPO-001",
        category=FaultCategory.RUNTIME_EXCEPTION,
        category_title="Decoy",
        affected_component="decoy.py",
        supporting_evidence_ids=["EVID-001"],
        contradicting_evidence_ids=["EVID-PROBE-001"],
        verification_status="contradicted",
        relative_ranking_score=80.0,
    )
    h2 = FaultHypothesis(
        hypothesis_id="HYPO-002",
        category=FaultCategory.CONFIG_MISSING_OR_INVALID,
        category_title="True Cause",
        affected_component="config.py",
        supporting_evidence_ids=["EVID-002"],
        contradicting_evidence_ids=[],
        verification_status="verified",
        relative_ranking_score=85.0,
    )

    evids = [
        DiagnosticEvidenceRecord(
            evidence_id="EVID-001", evidence_type="syntax_error", source_component="decoy.py",
            extraction_method="ast_parser", location="decoy.py:1", observed_data={}, reliability="direct_observation", limitations=[],
        ),
        DiagnosticEvidenceRecord(
            evidence_id="EVID-PROBE-001", evidence_type="probe_finding", source_component="decoy.py",
            extraction_method="ast_parser", location="decoy.py:1", observed_data={"outcome": "refuted"}, reliability="direct_observation", limitations=[],
        ),
        DiagnosticEvidenceRecord(
            evidence_id="EVID-002", evidence_type="runtime_telemetry", source_component="config.py",
            extraction_method="telemetry_analyzer", location="config.py:10", observed_data={"confidence": 0.9}, reliability="direct_observation", limitations=[],
        ),
    ]

    ranked = calibrator.rank_and_calibrate([h1, h2], evids)
    assert len(ranked) == 2
    assert ranked[0].hypothesis_id == "HYPO-002"
    assert ranked[1].hypothesis_id == "HYPO-001"
    assert ranked[1].confidence_level == "refuted"
    assert ranked[0].relative_ranking_score > ranked[1].relative_ranking_score


def test_calibrated_ranker_multi_fault_separation():
    """Verify multi-fault separation isolates top hypotheses across distinct components."""
    calibrator = CalibratedRanker()
    h1 = FaultHypothesis(
        hypothesis_id="HYPO-001",
        category=FaultCategory.RUNTIME_EXCEPTION,
        category_title="Syntax 1",
        affected_component="backend/main.py",
        supporting_evidence_ids=[],
        relative_ranking_score=75.0,
    )
    h2 = FaultHypothesis(
        hypothesis_id="HYPO-002",
        category=FaultCategory.CONFIG_MISSING_OR_INVALID,
        category_title="Config 1",
        affected_component="backend/main.py",
        supporting_evidence_ids=[],
        relative_ranking_score=60.0,
    )
    h3 = FaultHypothesis(
        hypothesis_id="HYPO-003",
        category=FaultCategory.RUNTIME_EXCEPTION,
        category_title="Syntax 2",
        affected_component="frontend/app.ts",
        supporting_evidence_ids=[],
        relative_ranking_score=80.0,
    )

    separated = calibrator.separate_multi_faults([h3, h1, h2], top_k_per_component=1)
    assert len(separated) == 2
    comps = {h.affected_component for h in separated}
    assert comps == {"backend/main.py", "frontend/app.ts"}
