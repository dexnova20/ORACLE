"""Tests for the 20-scenario generalization dataset and comparative ML ranking benchmark."""

import json
import os
import pytest

from ml.benchmark.ml_evaluation import run_comparative_ml_benchmark
from ml.dataset.generalization_dataset import (
    GENERALIZATION_SCENARIOS,
    materialize_generalization_fixtures,
)


def test_generalization_scenario_specifications():
    """Verify integrity of the 20 generalization scenarios."""
    assert len(GENERALIZATION_SCENARIOS) == 20

    ids = [s.scenario_id for s in GENERALIZATION_SCENARIOS]
    assert len(ids) == len(set(ids))  # All IDs unique

    # Check scenario distribution
    go_scenarios = [s for s in GENERALIZATION_SCENARIOS if s.ecosystem == "go"]
    assert len(go_scenarios) >= 4

    healthy_scenarios = [s for s in GENERALIZATION_SCENARIOS if s.is_healthy_control]
    assert len(healthy_scenarios) >= 3

    telemetry_scenarios = [s for s in GENERALIZATION_SCENARIOS if s.runtime_traceback or s.symptom_description]
    assert len(telemetry_scenarios) >= 6

    abstention_scenarios = [s for s in GENERALIZATION_SCENARIOS if s.is_abstention_case]
    assert len(abstention_scenarios) >= 1


def test_materialize_generalization_fixtures(tmp_path):
    """Verify fixture materialization generates expected files and directories."""
    paths = materialize_generalization_fixtures(str(tmp_path))
    assert len(paths) == 20

    for sc_id, sc_dir in paths.items():
        assert os.path.exists(sc_dir)
        assert os.path.isdir(sc_dir)
        files = os.listdir(sc_dir)
        assert len(files) >= 1


def test_comparative_ml_benchmark_execution(tmp_path):
    """Execute full comparative ML evaluation benchmark across all 20 generalization scenarios."""
    fixtures_dir = str(tmp_path / "fixtures")
    json_path = str(tmp_path / "reports" / "ml_comparison.json")
    md_path = str(tmp_path / "reports" / "ml_comparison.md")

    results = run_comparative_ml_benchmark(
        fixtures_dir=fixtures_dir,
        output_json_path=json_path,
        output_md_path=md_path,
    )

    assert results["total_scenarios"] == 20
    assert os.path.exists(json_path)
    assert os.path.exists(md_path)

    # Verify JSON content
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "models" in data
    assert "Naive Uniform Baseline" in data["models"]
    assert "Heuristic Baseline" in data["models"]
    assert "Calibrated Logistic Regression" in data["models"]
    assert "Calibrated Random Forest Ensemble" in data["models"]

    # Quantitative assertions
    rf_metrics = data["models"]["Calibrated Random Forest Ensemble"]
    logistic_metrics = data["models"]["Calibrated Logistic Regression"]
    naive_metrics = data["models"]["Naive Uniform Baseline"]

    # Top-1 accuracy must beat naive baseline and achieve >= 80% on generalization dataset
    assert rf_metrics["top_1_accuracy"] >= 0.80
    assert logistic_metrics["top_1_accuracy"] >= 0.80
    assert rf_metrics["top_1_accuracy"] > naive_metrics["top_1_accuracy"]

    # Brier score calibration metric
    assert rf_metrics["brier_score"] <= 0.28

    # Abstention quality on healthy/unsupported targets
    assert rf_metrics["abstention_quality"] >= 0.80

    # Latency should be sub-150ms per scenario
    assert rf_metrics["mean_latency_ms"] < 150.0
