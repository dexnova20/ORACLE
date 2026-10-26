"""Unit tests for ML experiment splitting, evaluation metrics, tracking, and baselines."""

import pytest
from ml.baselines import (
    BaselineType,
    get_baseline_specification,
    list_baseline_specifications,
)
from ml.dataset import (
    CaseFeatures,
    DiagnosticCase,
    ExpectedDiagnosticOutcome,
    GroundTruthLabel,
    ObservedSymptom,
    SYNTHETIC_CONFIG_MISSING_CASE,
    SYNTHETIC_DATABASE_UNREACHABLE_CASE,
    SYNTHETIC_INSUFFICIENT_EVIDENCE_CASE,
)
from ml.experiments import (
    DataLeakageError,
    ProjectAwareSplitter,
    ScenarioAwareSplitter,
    abstention_metrics,
    classification_metrics,
    diagnostic_cost_metrics,
    expected_calibration_error,
    false_positive_rate,
    generate_run_name,
    sanitize_parameters,
    top_k_ranking_accuracy,
    LocalTrackingConfig,
)
from ml.taxonomy import FaultCategory


# ---------------------------------------------------------------------------
# Splitting & Leakage Tests
# ---------------------------------------------------------------------------

def test_project_aware_splitter_guarantees_zero_overlap() -> None:
    """Verify that ProjectAwareSplitter guarantees disjoint project sets between train and test."""
    cases = [
        SYNTHETIC_DATABASE_UNREACHABLE_CASE,  # project_id: 'oracle-mock-project'
        SYNTHETIC_CONFIG_MISSING_CASE,        # project_id: 'oracle-mock-project'
        SYNTHETIC_INSUFFICIENT_EVIDENCE_CASE, # project_id: 'external-service-mock'
    ]

    splitter = ProjectAwareSplitter(test_projects={"external-service-mock"})
    train_cases, test_cases = splitter.split(cases)

    assert len(train_cases) == 2
    assert len(test_cases) == 1

    train_projects = {c.project_id for c in train_cases}
    test_projects = {c.project_id for c in test_cases}

    assert train_projects == {"oracle-mock-project"}
    assert test_projects == {"external-service-mock"}
    assert len(train_projects.intersection(test_projects)) == 0


def test_scenario_aware_splitter_guarantees_zero_overlap() -> None:
    """Verify that ScenarioAwareSplitter guarantees disjoint scenario sets."""
    cases = [
        SYNTHETIC_DATABASE_UNREACHABLE_CASE,  # scenario: 'scenario-postgres-down'
        SYNTHETIC_CONFIG_MISSING_CASE,        # scenario: 'scenario-missing-secret-key'
        SYNTHETIC_INSUFFICIENT_EVIDENCE_CASE, # scenario: 'scenario-intermittent-timeout'
    ]

    splitter = ScenarioAwareSplitter(test_scenarios={"scenario-postgres-down"})
    train_cases, test_cases = splitter.split(cases)

    assert len(train_cases) == 2
    assert len(test_cases) == 1
    assert test_cases[0].scenario_id == "scenario-postgres-down"

    train_scenarios = {c.scenario_id for c in train_cases}
    test_scenarios = {c.scenario_id for c in test_cases}
    assert len(train_scenarios.intersection(test_scenarios)) == 0


# ---------------------------------------------------------------------------
# Metric Calculation Tests
# ---------------------------------------------------------------------------

def test_top_k_ranking_accuracy() -> None:
    """Verify Top-1 and Top-3 accuracy calculations."""
    ranked_preds = [
        ["database_connectivity_schema", "network_timeout", "config_missing"],
        ["runtime_exception", "io_contract_violation", "data_validation"],
        ["unknown_insufficient_evidence", "config_missing", "runtime_exception"],
    ]
    ground_truth = [
        "database_connectivity_schema",  # Hit at rank 1
        "io_contract_violation",         # Hit at rank 2
        "config_missing",                # Hit at rank 2
    ]

    # Top-1 accuracy: only case 0 is hit at rank 1 -> 1/3 = 0.3333
    top1 = top_k_ranking_accuracy(ranked_preds, ground_truth, k=1)
    assert round(top1, 2) == 0.33

    # Top-3 accuracy: all three cases hit within top 3 -> 3/3 = 1.0
    top3 = top_k_ranking_accuracy(ranked_preds, ground_truth, k=3)
    assert top3 == 1.0


def test_classification_metrics_and_false_positive_rate() -> None:
    """Verify precision, recall, F1, and FPR calculation on multiclass targets."""
    preds = ["catA", "catB", "catA", "catB"]
    truth = ["catA", "catA", "catA", "catB"]

    metrics = classification_metrics(preds, truth)

    # catA: TP=2, FP=0, FN=1, TN=1 -> Prec=1.0, Rec=2/3=0.6667
    # catB: TP=1, FP=1, FN=0, TN=2 -> Prec=0.5, Rec=1.0
    assert metrics["accuracy"] == 0.75
    assert metrics["per_class"]["catA"]["precision"] == 1.0
    assert round(metrics["per_class"]["catA"]["recall"], 2) == 0.67
    assert metrics["per_class"]["catB"]["precision"] == 0.5
    assert metrics["per_class"]["catB"]["recall"] == 1.0

    fpr_b = false_positive_rate(preds, truth, target_label="catB")
    assert round(fpr_b, 2) == 0.33  # FP=1, TN=2 -> 1 / (1 + 2) = 0.333


def test_expected_calibration_error() -> None:
    """Verify Expected Calibration Error (ECE) calculation."""
    # Perfectly calibrated: 4 samples with confidence 1.0 all correct -> ECE = 0.0
    confidences = [1.0, 1.0, 1.0, 1.0]
    accuracies = [True, True, True, True]
    assert expected_calibration_error(confidences, accuracies, num_bins=5) == 0.0

    # Overconfident: confidence 0.9, but all incorrect -> ECE = 0.9
    confidences_bad = [0.9, 0.9, 0.9, 0.9]
    accuracies_bad = [False, False, False, False]
    assert expected_calibration_error(confidences_bad, accuracies_bad, num_bins=5) == 0.9


def test_abstention_metrics() -> None:
    """Verify abstention metrics when evidence is insufficient."""
    preds = ["catA", "unknown_insufficient_evidence", "unknown_insufficient_evidence", "catB"]
    truth = ["catA", "unknown_insufficient_evidence", "catA", "catB"]

    res = abstention_metrics(preds, truth)
    # TP=1, FP=1, FN=0
    assert res["abstention_precision"] == 0.5
    assert res["abstention_recall"] == 1.0
    assert res["coverage"] == 0.5  # 2 out of 4 non-abstained


def test_diagnostic_cost_metrics() -> None:
    """Verify latency summary statistics."""
    latencies = [10.0, 20.0, 30.0, 40.0, 100.0]
    costs = [1.0, 1.0, 2.0, 1.0, 3.0]

    res = diagnostic_cost_metrics(latencies, costs)
    assert res["mean_latency_ms"] == 40.0
    assert res["p95_latency_ms"] == 100.0
    assert res["mean_probe_cost"] == 1.6


# ---------------------------------------------------------------------------
# Tracking & Reproducibility Tests
# ---------------------------------------------------------------------------

def test_parameter_sanitization_redacts_secrets() -> None:
    """Verify secrets and connection credentials are removed before experiment logging."""
    raw_params = {
        "learning_rate": 0.01,
        "max_depth": 6,
        "database_url": "postgresql://admin:super_secret_password@10.0.0.1:5432/proddb",
        "api_token": "sk-1234567890abcdef",
        "aws_secret_key": "xyz987654321",
        "target_endpoint": "https://service_user:super_secret_token@api.example.com/v1",
    }

    sanitized = sanitize_parameters(raw_params)

    assert sanitized["learning_rate"] == 0.01
    assert sanitized["max_depth"] == 6
    assert sanitized["api_token"] == "[REDACTED]"
    assert sanitized["aws_secret_key"] == "[REDACTED]"
    assert sanitized["database_url"] == "[REDACTED]"
    assert "super_secret_password" not in str(sanitized)
    assert "super_secret_token" not in str(sanitized)
    assert "[REDACTED]:[REDACTED]@" in sanitized["target_endpoint"]


def test_generate_run_name() -> None:
    """Verify run name formatting convention."""
    run_name = generate_run_name(
        model_name="XGBoost Classifier",
        split_strategy="Project Aware",
        taxonomy_version="1.0.0",
    )
    assert run_name == "oracle-diag-v1.0.0-xgboost_classifier-project_aware"


def test_local_tracking_config() -> None:
    """Verify local tracking configuration defaults."""
    cfg = LocalTrackingConfig()
    assert cfg.tracking_uri.startswith("file:")
    assert cfg.dvc_enabled is False


# ---------------------------------------------------------------------------
# Baseline Registry Tests
# ---------------------------------------------------------------------------

def test_all_six_baseline_specifications_registered() -> None:
    """Verify all 6 baseline progression stages are formally specified."""
    expected_baselines = {
        BaselineType.DETERMINISTIC_RULES,
        BaselineType.STATISTICAL_FREQUENCY,
        BaselineType.ISOLATION_FOREST_ANOMALY,
        BaselineType.XGBOOST_FAULT_RANKER,
        BaselineType.ADAPTIVE_TEST_SELECTOR,
        BaselineType.PRETRAINED_EMBEDDINGS_DL,
    }

    specs = list_baseline_specifications()
    assert len(specs) == 6

    registered_types = {s.baseline_type for s in specs}
    assert registered_types == expected_baselines

    for spec in specs:
        assert len(spec.name.strip()) > 5
        assert len(spec.input_features) >= 1
        assert len(spec.output_format.strip()) > 5
        assert len(spec.underlying_assumptions) >= 1
        assert len(spec.baseline_comparison.strip()) > 10
        assert len(spec.expected_failure_modes) >= 1
        assert len(spec.training_requirements.strip()) > 5
        assert len(spec.evaluation_role.strip()) > 5
