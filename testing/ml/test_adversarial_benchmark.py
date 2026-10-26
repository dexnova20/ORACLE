"""Automated adversarial benchmark validation test suite for ORACLE (Implementation 012).

Tests the 20-scenario adversarial benchmark suite, ground-truth isolation,
clean control false-positive rates, deliberate abstention, and multiple-fault separation.
"""

import os
import re
import sys
import pytest

from ml.benchmark.adaptive_runner import AdaptiveBenchmarkRunner, AdaptiveBenchmarkSummary
from ml.benchmark.evaluation_report import ReliabilityEvaluator
from ml.benchmark.scenarios import get_benchmark_scenarios, get_ground_truth_manifest
from ml.taxonomy.fault_taxonomy import FaultCategory, TAXONOMY_VERSION


@pytest.fixture
def adaptive_runner() -> AdaptiveBenchmarkRunner:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fixtures_dir = os.path.abspath(os.path.join(current_dir, "..", "fixtures", "benchmark"))
    return AdaptiveBenchmarkRunner(fixtures_base_dir=fixtures_dir, enable_dynamic=False)


def test_adversarial_benchmark_all_scenarios_evaluated(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify that all 60 benchmark scenarios are evaluated with 100% supported accuracy and 0% FPR."""
    summary: AdaptiveBenchmarkSummary = adaptive_runner.run_all()

    assert summary.total_scenarios == 60
    assert summary.supported_scenarios_evaluated == 56
    assert summary.accuracy_on_supported == 100.0
    assert summary.healthy_control_false_positive_rate == 0.0
    assert summary.abstention_accuracy == 100.0
    assert summary.unsafe_probe_rejection_rate == 100.0
    assert summary.repeated_probes_prevented_rate == 100.0
    assert summary.mean_iterations_per_scenario >= 1.0


def test_leak_free_adversarial_manifest(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify that all 20 scenarios have neutral identifiers without ground-truth leakage."""
    scenario_id_pattern = re.compile(r"^CASE-\d{3}$")
    project_id_pattern = re.compile(r"^PRJ-\d{3}$")

    for s in adaptive_runner.scenarios:
        assert scenario_id_pattern.match(s.scenario_id)
        assert project_id_pattern.match(s.project_id)

        # Ensure no ground-truth fields exist on scenario objects
        assert not hasattr(s, "taxonomy_category")
        assert not hasattr(s, "root_cause_component")
        assert not hasattr(s, "expected_diagnostic_outcome")

        # Ensure IDs do not leak category names
        lowered = (s.scenario_id + s.project_id).lower()
        for cat in FaultCategory:
            assert cat.value not in lowered
        assert "syntax" not in lowered
        assert "error" not in lowered
        assert "import" not in lowered


def test_healthy_controls_across_structural_variations(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify that all 5 healthy controls produce zero false-positive fault hypotheses."""
    control_ids = {"CASE-001", "CASE-009", "CASE-014", "CASE-015", "CASE-020"}
    controls = [s for s in adaptive_runner.scenarios if s.scenario_id in control_ids]
    assert len(controls) == 5

    for c in controls:
        res = adaptive_runner.evaluate_scenario(c)
        assert res.evaluation_outcome == "correct"
        assert res.hypotheses_count == 0
        assert "zero false positive" in res.explanation


def test_multiple_fault_scenarios_identified(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify that multiple simultaneous fault scenarios (CASE-012, CASE-013, CASE-016) separate independent faults."""
    multi_ids = ["CASE-012", "CASE-013", "CASE-016"]
    for mid in multi_ids:
        sc = next(s for s in adaptive_runner.scenarios if s.scenario_id == mid)
        res = adaptive_runner.evaluate_scenario(sc)
        assert res.evaluation_outcome == "correct"
        # Must execute at least 2 independent probes
        assert res.executed_probes_count >= 2


def test_abstention_on_empty_and_polyglot_projects(adaptive_runner: AdaptiveBenchmarkRunner):
    """Verify that empty repo (CASE-010) and polyglot C++/Java repo (CASE-019) trigger deliberate abstention."""
    for aid in ("CASE-010", "CASE-019"):
        sc = next(s for s in adaptive_runner.scenarios if s.scenario_id == aid)
        res = adaptive_runner.evaluate_scenario(sc)
        assert res.evaluation_outcome in ("abstained", "correct")
        assert res.confidence_level == "uncertain"
        assert res.stopping_reason == "deliberate_abstention"
