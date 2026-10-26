"""Automated test suite verifying the adaptive benchmark runner, probe planning, and leakage isolation."""

import os
import sys
import pytest

from ml.benchmark.adaptive_runner import AdaptiveBenchmarkRunner, AdaptiveBenchmarkSummary
from ml.benchmark.scenarios import get_benchmark_scenarios, get_ground_truth_manifest
from ml.taxonomy.fault_taxonomy import FaultCategory


@pytest.fixture
def adaptive_runner() -> AdaptiveBenchmarkRunner:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fixtures_dir = os.path.abspath(os.path.join(current_dir, "..", "fixtures", "benchmark"))
    return AdaptiveBenchmarkRunner(fixtures_base_dir=fixtures_dir, enable_dynamic=False)


def test_adaptive_benchmark_all_scenarios_evaluated(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify adaptive benchmark runs across all scenarios with 100% supported accuracy."""
    summary: AdaptiveBenchmarkSummary = adaptive_runner.run_all()

    assert summary.total_scenarios == len(adaptive_runner.scenarios)
    assert summary.supported_scenarios_evaluated >= 7
    assert summary.accuracy_on_supported == 100.0
    assert summary.healthy_control_false_positive_rate == 0.0
    assert summary.abstention_accuracy == 100.0
    assert summary.unsafe_probe_rejection_rate == 100.0
    assert summary.repeated_probes_prevented_rate == 100.0
    assert summary.mean_iterations_per_scenario >= 1.0


def test_adaptive_benchmark_healthy_controls_zero_false_positives(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify that healthy controls emit zero fault hypotheses."""
    scenarios = [s for s in adaptive_runner.scenarios if s.is_healthy_control]
    assert len(scenarios) >= 2

    for sc in scenarios:
        res = adaptive_runner.evaluate_scenario(sc)
        assert res.evaluation_outcome == "correct"
        assert res.hypotheses_count == 0
        assert "zero false positive" in res.explanation


def test_adaptive_benchmark_deliberate_abstention_case_10(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify that empty repository stub triggers deliberate abstention."""
    sc10 = next(s for s in adaptive_runner.scenarios if s.scenario_id == "CASE-010")
    res = adaptive_runner.evaluate_scenario(sc10)

    assert res.evaluation_outcome == "abstained"
    assert res.top_hypothesis_category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE.value
    assert res.confidence_level == "uncertain"
    assert res.stopping_reason == "deliberate_abstention"


def test_adaptive_benchmark_downstream_blocked_case_11(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify CASE-011 diagnoses upstream fault and captures downstream blocked state."""
    sc11 = next(s for s in adaptive_runner.scenarios if s.scenario_id == "CASE-011")
    res = adaptive_runner.evaluate_scenario(sc11)

    assert res.evaluation_outcome == "correct"
    assert res.top_hypothesis_category == FaultCategory.RUNTIME_EXCEPTION.value
    assert "static_ast_syntax_check" in res.selected_probes


def test_adaptive_benchmark_unsafe_dynamic_rejection_without_docker(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify that dynamic test scenarios are safely marked unsupported when isolation is absent."""
    dynamic_scenarios = [s for s in adaptive_runner.scenarios if not s.is_supported_statically]
    assert len(dynamic_scenarios) == 4

    for sc in dynamic_scenarios:
        res = adaptive_runner.evaluate_scenario(sc)
        assert res.evaluation_outcome == "unsupported"
        assert "Host execution was prohibited" in res.explanation
