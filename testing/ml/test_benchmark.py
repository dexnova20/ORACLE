"""Comprehensive automated tests for ORACLE Controlled Fault-Injection Benchmark (Implementation 008)."""

import os
import re
import sys
import pytest

from ml.benchmark import (
    BENCHMARK_SCHEMA_VERSION,
    BenchmarkRunner,
    BenchmarkScenario,
    DiagnosticEvidence,
    EvidenceState,
    GroundTruthManifest,
    ScenarioGroundTruth,
    get_benchmark_scenarios,
    get_ground_truth_manifest,
    run_benchmark,
)
from ml.dataset.schema import (
    CaseFeatures,
    DiagnosticCase,
    ExpectedDiagnosticOutcome,
    GroundTruthLabel,
    ObservedSymptom,
)
from ml.experiments.evaluation import classification_metrics, false_positive_rate
from ml.experiments.splitting import ProjectAwareSplitter, ScenarioAwareSplitter
from ml.taxonomy.fault_taxonomy import FaultCategory, TAXONOMY_VERSION


@pytest.fixture
def runner() -> BenchmarkRunner:
    """Fixture providing an initialized BenchmarkRunner."""
    return BenchmarkRunner()


def test_benchmark_manifest_and_schema_validation(runner: BenchmarkRunner):
    """Verify that all scenarios and ground-truth records conform to schema specifications."""
    scenarios = runner.scenarios
    manifest = runner.manifest

    assert len(scenarios) >= 10
    assert len(manifest.entries) >= 10
    assert manifest.manifest_version == BENCHMARK_SCHEMA_VERSION

    for scenario in scenarios:
        assert scenario.benchmark_version == BENCHMARK_SCHEMA_VERSION
        assert manifest.contains(scenario.scenario_id)
        gt = manifest.get(scenario.scenario_id)
        assert gt is not None
        assert gt.taxonomy_version == TAXONOMY_VERSION
        assert gt.scenario_id == scenario.scenario_id


def test_ground_truth_isolation_and_no_leakage(runner: BenchmarkRunner):
    """Ensure ground-truth labels and outcomes are strictly isolated from diagnostic inputs."""
    scenarios = runner.scenarios

    # BenchmarkScenario objects presented to the diagnostic engine must not have ground truth fields
    for s in scenarios:
        assert not hasattr(s, "taxonomy_category")
        assert not hasattr(s, "root_cause_component")
        assert not hasattr(s, "injected_fault_description")
        assert not hasattr(s, "expected_diagnostic_outcome")

    # DiagnosticEvidence.to_diagnostic_input() must never contain forbidden leakage keywords
    summary = runner.run_all(run_id="test-isolation")
    for case_res in summary.case_results:
        diag_input = case_res.evidence.to_diagnostic_input()
        serialized = str(diag_input).lower()
        assert "root_cause" not in serialized
        assert "ground_truth" not in serialized
        assert "injected_fault" not in serialized


def test_neutral_identifiers_and_no_giveaways(runner: BenchmarkRunner):
    """Ensure scenario IDs and project IDs use neutral identifiers without giving away root causes."""
    scenario_id_pattern = re.compile(r"^CASE-\d{3}$")
    project_id_pattern = re.compile(r"^PRJ-\d{3}$")

    for s in runner.scenarios:
        assert scenario_id_pattern.match(s.scenario_id), f"Scenario ID {s.scenario_id} is not neutral"
        assert project_id_pattern.match(s.project_id), f"Project ID {s.project_id} is not neutral"

        # Assert no fault category names are leaked in the IDs
        lower_id = (s.scenario_id + s.project_id).lower()
        for cat in FaultCategory:
            assert cat.value not in lower_id
        assert "error" not in lower_id
        assert "syntax" not in lower_id
        assert "missing" not in lower_id


def test_healthy_controls_zero_false_positive(runner: BenchmarkRunner):
    """Verify that healthy control projects produce zero false positives."""
    summary = runner.run_all(run_id="test-controls")
    healthy_results = [r for r in summary.case_results if r.scenario_id in ("CASE-001", "CASE-009")]

    assert len(healthy_results) == 2
    for r in healthy_results:
        assert r.is_supported_statically is True
        assert r.observed_fault_category is None
        assert r.evaluation_outcome == "correct_control"

    assert summary.false_positive_count == 0
    assert summary.false_positive_rate == 0.0


def test_syntax_error_scenario_detection(runner: BenchmarkRunner):
    """Verify that Python syntax errors are observed with line provenance and diagnosed correctly."""
    scenario = next(s for s in runner.scenarios if s.scenario_id == "CASE-002")
    res = runner.evaluate_scenario(scenario)

    assert res.is_supported_statically is True
    assert res.observed_fault_category == FaultCategory.RUNTIME_EXCEPTION
    assert res.evaluation_outcome == "correct"
    assert len(res.evidence.syntax_errors) == 1

    err = res.evidence.syntax_errors[0]
    assert err["file_path"] == "processor.py"
    assert err["line_number"] == 6
    assert "(" in err["error_message"] or "never closed" in err["error_message"]


def test_unresolved_internal_import_scenario(runner: BenchmarkRunner):
    """Verify that unresolved internal relative imports are extracted and diagnosed."""
    scenario = next(s for s in runner.scenarios if s.scenario_id == "CASE-003")
    res = runner.evaluate_scenario(scenario)

    assert res.is_supported_statically is True
    assert res.observed_fault_category == FaultCategory.DEPENDENCY_IMPORT_FAILURE
    assert res.evaluation_outcome == "correct"
    assert len(res.evidence.unresolved_imports) >= 1

    unresolved = res.evidence.unresolved_imports[0]
    assert "non_existent_helper" in unresolved["target"]
    assert unresolved["line"] == 3


def test_external_dependency_scenario(runner: BenchmarkRunner):
    """Verify that external third-party package dependencies are captured in observable evidence."""
    scenario = next(s for s in runner.scenarios if s.scenario_id == "CASE-004")
    res = runner.evaluate_scenario(scenario)

    assert res.is_supported_statically is True
    assert res.observed_fault_category == FaultCategory.DEPENDENCY_IMPORT_FAILURE
    assert res.evaluation_outcome == "correct"
    assert "pkg:requests" in res.evidence.external_imports
    assert "pkg:stripe" in res.evidence.external_imports


def test_unsupported_dynamic_scenarios_cleanly_flagged(runner: BenchmarkRunner):
    """Verify that scenarios requiring dynamic execution are marked unsupported without fabricating evidence."""
    unsupported_ids = {"CASE-005", "CASE-006", "CASE-007", "CASE-008"}
    summary = runner.run_all(run_id="test-unsupported")
    unsupported_results = [r for r in summary.case_results if r.scenario_id in unsupported_ids]

    assert len(unsupported_results) == 4
    for r in unsupported_results:
        assert r.is_supported_statically is False
        assert r.evaluation_outcome == "unsupported_analysis"
        assert r.evidence.evidence_state == EvidenceState.UNSUPPORTED
        assert r.observed_fault_category is None
        # Assert no fake stack traces or socket errors are fabricated in evidence
        assert len(r.evidence.syntax_errors) == 0
        assert len(r.evidence.unresolved_imports) == 0


def test_misleading_symptoms_do_not_cause_false_positive(runner: BenchmarkRunner):
    """Verify that non-causal historical comments mentioning errors do not mislead the inspector."""
    scenario = next(s for s in runner.scenarios if s.scenario_id == "CASE-009")
    res = runner.evaluate_scenario(scenario)

    assert res.is_supported_statically is True
    # The inspector must NOT flag this as database_connectivity_schema based on a comment
    assert res.observed_fault_category is None
    assert res.evaluation_outcome == "correct_control"


def test_deliberate_abstention_on_insufficient_evidence(runner: BenchmarkRunner):
    """Verify that empty repositories with zero analyzable code trigger deliberate abstention."""
    scenario = next(s for s in runner.scenarios if s.scenario_id == "CASE-010")
    res = runner.evaluate_scenario(scenario)

    assert res.is_supported_statically is True
    assert res.observed_fault_category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE
    assert res.evaluation_outcome == "correct_abstention"
    assert res.evidence.total_files_analyzed == 0


def test_repeat_run_determinism(runner: BenchmarkRunner):
    """Verify that repeat runs against identical fixtures yield identical diagnostic outcomes."""
    summary1 = runner.run_all(run_id="run-det-1")
    summary2 = runner.run_all(run_id="run-det-2")

    assert summary1.total_scenarios == summary2.total_scenarios
    assert summary1.supported_scenarios == summary2.supported_scenarios
    assert summary1.unsupported_scenarios == summary2.unsupported_scenarios
    assert summary1.static_diagnostic_accuracy == summary2.static_diagnostic_accuracy
    assert summary1.false_positive_rate == summary2.false_positive_rate
    assert summary1.abstention_count == summary2.abstention_count

    for r1, r2 in zip(summary1.case_results, summary2.case_results):
        assert r1.scenario_id == r2.scenario_id
        assert r1.observed_fault_category == r2.observed_fault_category
        assert r1.evaluation_outcome == r2.evaluation_outcome
        assert r1.evidence.syntax_errors == r2.evidence.syntax_errors
        assert r1.evidence.unresolved_imports == r2.evidence.unresolved_imports
        assert r1.evidence.external_imports == r2.evidence.external_imports


def test_project_and_scenario_split_leakage(runner: BenchmarkRunner):
    """Verify that cases built from benchmark scenarios guarantee zero group or scenario leakage."""
    cases = []
    manifest = runner.manifest
    for s in runner.scenarios:
        gt = manifest.get(s.scenario_id)
        case = DiagnosticCase(
            case_id=f"case-{s.scenario_id}",
            project_id=s.project_id,
            scenario_id=s.scenario_id,
            is_synthetic=True,
            features=CaseFeatures(
                component_identifiers=[s.project_id],
                symptoms=[
                    ObservedSymptom(
                        symptom_type="inspection_signal",
                        source="static_inspector",
                        message_pattern=f"signal from {s.scenario_id}",
                    )
                ],
            ),
            ground_truth=GroundTruthLabel(
                root_cause_category=gt.taxonomy_category or FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE,
                root_cause_component=gt.root_cause_component,
                root_cause_detail=gt.injected_fault_description,
            ),
            expected_outcome=ExpectedDiagnosticOutcome(
                primary_action=gt.expected_diagnostic_outcome,
            ),
        )
        cases.append(case)

    # Test ProjectAwareSplitter with explicit holdout set
    p_splitter = ProjectAwareSplitter(test_projects={"PRJ-002", "PRJ-004", "PRJ-006"})
    p_train, p_test = p_splitter.split(cases)
    p_train_projects = {c.project_id for c in p_train}
    p_test_projects = {c.project_id for c in p_test}
    assert p_train_projects.isdisjoint(p_test_projects), "Project leakage detected!"
    assert len(p_test) == 3

    # Test ScenarioAwareSplitter with explicit holdout set
    s_splitter = ScenarioAwareSplitter(test_scenarios={"CASE-003", "CASE-007"})
    s_train, s_test = s_splitter.split(cases)
    s_train_scenarios = {c.scenario_id for c in s_train}
    s_test_scenarios = {c.scenario_id for c in s_test}
    assert s_train_scenarios.isdisjoint(s_test_scenarios), "Scenario leakage detected!"
    assert len(s_test) == 2


def test_runner_handles_missing_fixture_gracefully(runner: BenchmarkRunner):
    """Verify that a scenario pointing to a non-existent directory fails safely without crashing."""
    bogus_scenario = BenchmarkScenario(
        scenario_id="CASE-999",
        project_id="PRJ-999",
        fixture_relative_path="non_existent_folder_xyz_123",
        is_healthy_control=False,
        is_supported_statically=True,
        reproduction_method="None",
        safety_classification="safe_static_only",
    )

    res = runner.evaluate_scenario(bogus_scenario)
    assert res.evidence.status == "failed"
    assert res.evidence.evidence_state == EvidenceState.FAILED
    assert res.evaluation_outcome == "incorrect"
    assert "missing" in res.explanation.lower()


def test_no_untrusted_code_execution_during_benchmark(runner: BenchmarkRunner):
    """Verify that executing the benchmark did not import any fixture modules into sys.modules."""
    fixture_module_names = {"processor", "service", "client", "config", "db", "api_client", "transform", "worker"}

    # Run the entire benchmark
    runner.run_all(run_id="test-no-exec")

    # Assert that none of the fixture module names are in sys.modules
    for mod_name in fixture_module_names:
        assert mod_name not in sys.modules, f"Fixture module '{mod_name}' was executed/imported into sys.modules!"


def test_honest_metrics_and_undefined_handling(runner: BenchmarkRunner):
    """Verify that undefined metrics are handled explicitly and ranking accuracy reports None."""
    summary = runner.run_all(run_id="test-metrics")

    # Ranking accuracy must be None because no ranking ML model is active
    assert summary.top_k_ranking_accuracy is None

    # Test classification_metrics handles empty inputs without crashing
    empty_res = classification_metrics([], [])
    assert empty_res["accuracy"] == 0.0
    assert empty_res["macro_f1"] == 0.0

    # Test false_positive_rate with zero denominator returns 0.0
    fpr = false_positive_rate(["a", "b"], ["a", "b"], target_label="c")
    assert fpr == 0.0
