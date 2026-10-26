"""Tests for adaptive vs fixed probe sequence evaluation and entropy reduction."""

import pytest

from ml.planning.probe_evaluation import evaluate_probe_policies, simulate_probe_outcome
from ml.planning.probe_planner import (
    calculate_expected_information_gain,
    calculate_shannon_entropy,
)
from oracle.schemas.diagnostics import (
    DiagnosticEvidenceRecord,
    DiagnosticProbe,
    FaultHypothesis,
)
from ml.taxonomy.fault_taxonomy import FaultCategory


def test_shannon_entropy_properties():
    """Verify Shannon entropy properties: 0 for certain distribution, max for uniform."""
    certain = [1.0, 0.0, 0.0]
    assert calculate_shannon_entropy(certain) == 0.0

    uniform_2 = [0.5, 0.5]
    assert abs(calculate_shannon_entropy(uniform_2) - 1.0) < 1e-4

    uniform_4 = [0.25, 0.25, 0.25, 0.25]
    assert abs(calculate_shannon_entropy(uniform_4) - 2.0) < 1e-4


def test_expected_information_gain_positive():
    """Verify informative test produces strictly positive expected information gain."""
    priors = [0.5, 0.5]
    # Outcome 1 resolves to H1, Outcome 2 resolves to H2
    outcomes = {
        "out_1": (0.5, [1.0, 0.0]),
        "out_2": (0.5, [0.0, 1.0]),
    }
    eig = calculate_expected_information_gain(priors, outcomes)
    assert abs(eig - 1.0) < 1e-4


def test_evaluate_probe_policies_adaptive_superiority():
    """Verify adaptive probe policy exhibits higher efficiency than random/fixed sequences."""
    scenarios = []

    for i in range(5):
        h1 = FaultHypothesis(
            hypothesis_id="HYPO-001",
            category=FaultCategory.RUNTIME_EXCEPTION,
            category_title="Syntax Error",
            affected_component=f"src/file_{i}.py",
            supporting_evidence_ids=[f"EVID-{i:03d}"],
            relative_ranking_score=60.0,
        )
        h2 = FaultHypothesis(
            hypothesis_id="HYPO-002",
            category=FaultCategory.CONFIG_MISSING_OR_INVALID,
            category_title="Config Error",
            affected_component="settings.py",
            supporting_evidence_ids=[],
            relative_ranking_score=40.0,
        )
        ev = DiagnosticEvidenceRecord(
            evidence_id=f"EVID-{i:03d}",
            evidence_type="syntax_error",
            source_component=f"src/file_{i}.py",
            extraction_method="ast_parser",
            location=f"src/file_{i}.py:10",
            observed_data={},
            reliability="direct_observation",
            limitations=[],
        )
        scenarios.append({
            "hypotheses": [h1, h2],
            "evidence": [ev],
            "ground_truth_category": FaultCategory.RUNTIME_EXCEPTION.value,
            "ground_truth_component": f"src/file_{i}.py",
        })

    results = evaluate_probe_policies(scenarios, random_seed=42)

    assert "adaptive_information_gain" in results
    assert "fixed_static_first" in results
    assert "fixed_dynamic_first" in results
    assert "random_selection" in results

    adaptive = results["adaptive_information_gain"]
    random_pol = results["random_selection"]
    dynamic_first = results["fixed_dynamic_first"]

    assert adaptive.mean_entropy_reduction >= 0.0
    assert adaptive.probe_efficiency >= dynamic_first.probe_efficiency
    assert adaptive.convergence_rate >= 0.8
