"""Automated unit and integration test suite for ORACLE Diagnostic Reliability (Implementation 012).

Verifies:
- Order invariance and commutativity in heuristic hypothesis ranking.
- Evidence deduplication preventing confidence score inflation.
- Multi-fault separation across independent components.
- Immunity to misleading comments, docstrings, and non-fatal structural variations.
- Downstream cascade reasoning and blocked component preservation.
- Deliberate abstention on unsupported polyglot/non-Python projects.
- Host safety gating with zero untrusted code execution.
- Evaluation harness reproducibility and metric contracts.
"""

import os
import sys
import uuid
import pytest

from ml.benchmark.evaluation_report import ReliabilityEvaluator, run_and_save_report
from ml.benchmark.scenarios import get_benchmark_scenarios, get_ground_truth_manifest
from ml.ranking.heuristic_ranker import HeuristicRankerConfig, rank_hypotheses
from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.diagnostics.service import DiagnosticOrchestrator
from oracle.models.repository import Repository, SourceType
from oracle.schemas.diagnostics import (
    DiagnosticComponent,
    DiagnosticEvidenceRecord,
    DiagnosticReport,
    DiagnosticRunRequest,
    DiagnosticSystemMap,
    FaultHypothesis,
)


@pytest.fixture
def fixtures_dir() -> str:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(repo_root, "testing", "fixtures", "benchmark")


@pytest.fixture
def orchestrator() -> DiagnosticOrchestrator:
    return DiagnosticOrchestrator()


def test_order_invariant_hypothesis_scoring():
    """Verify that evidence arrival order does not change the heuristic ranking score."""
    e1 = DiagnosticEvidenceRecord(
        evidence_id="EVID-001",
        evidence_type="syntax_error",
        source_component="file:main.py",
        extraction_method="ast_parser",
        reliability="limited_context",
    )
    e2 = DiagnosticEvidenceRecord(
        evidence_id="EVID-002",
        evidence_type="syntax_error",
        source_component="file:main.py",
        extraction_method="ast_parser",
        reliability="direct_observation",
    )

    evidence_set = [e1, e2]

    # Hypothesis with order [EVID-001, EVID-002]
    h_order_a = FaultHypothesis(
        hypothesis_id="HYPO-A",
        category=FaultCategory.RUNTIME_EXCEPTION,
        category_title="Runtime Exception",
        affected_component="main.py",
        supporting_evidence_ids=["EVID-001", "EVID-002"],
        verification_status="supported",
    )

    # Hypothesis with reversed order [EVID-002, EVID-001]
    h_order_b = FaultHypothesis(
        hypothesis_id="HYPO-B",
        category=FaultCategory.RUNTIME_EXCEPTION,
        category_title="Runtime Exception",
        affected_component="main.py",
        supporting_evidence_ids=["EVID-002", "EVID-001"],
        verification_status="supported",
    )

    ranked = rank_hypotheses([h_order_a, h_order_b], evidence_set)
    assert len(ranked) == 2

    # Scores must be strictly equal regardless of evidence list order
    score_a = next(h.relative_ranking_score for h in ranked if h.hypothesis_id == "HYPO-A")
    score_b = next(h.relative_ranking_score for h in ranked if h.hypothesis_id == "HYPO-B")

    assert score_a == score_b
    # Expected: primary direct obs (35.0) + additional (5.0) + supported bonus (15.0) = 55.0
    assert score_a == 55.0


def test_evidence_deduplication_prevents_score_inflation():
    """Verify that duplicate evidence IDs do not artificially inflate confidence."""
    e1 = DiagnosticEvidenceRecord(
        evidence_id="EVID-SYNTAX-001",
        evidence_type="syntax_error",
        source_component="file:app.py",
        extraction_method="ast_parser",
        reliability="direct_observation",
    )

    h_single = FaultHypothesis(
        hypothesis_id="HYPO-SINGLE",
        category=FaultCategory.RUNTIME_EXCEPTION,
        category_title="Runtime Exception",
        affected_component="app.py",
        supporting_evidence_ids=["EVID-SYNTAX-001"],
        verification_status="candidate",
    )

    h_duplicate = FaultHypothesis(
        hypothesis_id="HYPO-DUP",
        category=FaultCategory.RUNTIME_EXCEPTION,
        category_title="Runtime Exception",
        affected_component="app.py",
        supporting_evidence_ids=[
            "EVID-SYNTAX-001",
            "EVID-SYNTAX-001",
            "EVID-SYNTAX-001",
            "EVID-SYNTAX-001",
        ],
        verification_status="candidate",
    )

    ranked = rank_hypotheses([h_single, h_duplicate], [e1])
    score_single = next(h.relative_ranking_score for h in ranked if h.hypothesis_id == "HYPO-SINGLE")
    score_dup = next(h.relative_ranking_score for h in ranked if h.hypothesis_id == "HYPO-DUP")

    assert score_single == score_dup
    # 35.0 base + 5.0 candidate = 40.0
    assert score_dup == 40.0


def test_multiple_simultaneous_syntax_faults_separated(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify that proj_12 with independent syntax defects in service_a.py and service_b.py emits separate hypotheses."""
    fixture_path = os.path.join(fixtures_dir, "proj_12")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-012",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )

    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    verified_components = {
        h.affected_component
        for h in report.hypotheses
        if h.verification_status == "verified" and h.category == FaultCategory.RUNTIME_EXCEPTION
    }

    assert "service_a.py" in verified_components
    assert "service_b.py" in verified_components
    assert len(verified_components) >= 2

    # Verify both AST syntax check probes were executed
    executed_types = [p.probe_type for p in report.executed_probes]
    assert executed_types.count("static_ast_syntax_check") >= 2


def test_multiple_simultaneous_mixed_faults_separated(orchestrator: DiagnosticOrchestrator, fixtures_dir: str):
    """Verify that proj_13 with syntax error in parser.py and unresolved import in client.py emits separate hypotheses."""
    fixture_path = os.path.join(fixtures_dir, "proj_13")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-013",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )

    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    categories_by_component = {
        h.affected_component: h.category
        for h in report.hypotheses
        if h.verification_status == "verified"
    }

    assert "parser.py" in categories_by_component
    assert categories_by_component["parser.py"] == FaultCategory.RUNTIME_EXCEPTION

    assert "client.py" in categories_by_component
    assert categories_by_component["client.py"] == FaultCategory.DEPENDENCY_IMPORT_FAILURE


def test_downstream_independently_broken_component_not_marked_clean(
    orchestrator: DiagnosticOrchestrator, fixtures_dir: str
):
    """Verify that proj_16 identifies syntax errors in both upstream and downstream components."""
    fixture_path = os.path.join(fixtures_dir, "proj_16")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-016",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )

    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    verified_components = {
        h.affected_component
        for h in report.hypotheses
        if h.verification_status == "verified"
    }

    assert "upstream.py" in verified_components
    assert "downstream.py" in verified_components


def test_clean_project_structural_variations_zero_false_positives(
    orchestrator: DiagnosticOrchestrator, fixtures_dir: str
):
    """Verify that proj_14 with src/ layout and dataclasses produces zero false positives."""
    fixture_path = os.path.join(fixtures_dir, "proj_14")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-014",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )

    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    assert len(report.hypotheses) == 0
    assert report.stopping_reason == "sufficient_evidence_verified"


def test_clean_project_misleading_docstrings_zero_false_positives(
    orchestrator: DiagnosticOrchestrator, fixtures_dir: str
):
    """Verify that proj_15 with error strings in docstrings produces zero false positives."""
    fixture_path = os.path.join(fixtures_dir, "proj_15")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-015",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )

    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    assert len(report.hypotheses) == 0
    assert report.stopping_reason == "sufficient_evidence_verified"


def test_safe_default_env_var_no_false_positive_config_fault(
    orchestrator: DiagnosticOrchestrator, fixtures_dir: str
):
    """Verify that proj_20 referencing os.getenv with a default does not manufacture a config fault."""
    fixture_path = os.path.join(fixtures_dir, "proj_20")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-020",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )

    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    assert len(report.hypotheses) == 0


def test_unsupported_non_python_project_deliberate_abstention(
    orchestrator: DiagnosticOrchestrator, fixtures_dir: str
):
    """Verify that proj_19 containing only unsupported languages (C++ and Rust) triggers deliberate abstention."""
    fixture_path = os.path.join(fixtures_dir, "proj_19")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-019",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )

    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(capabilities=["static_inspection", "evidence_collection", "adaptive_probing"]),
    )

    assert len(report.hypotheses) == 1
    h = report.hypotheses[0]
    assert h.category == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE
    assert h.confidence_level == "uncertain"
    assert report.stopping_reason == "deliberate_abstention"


def test_unsafe_dynamic_probe_rejection_without_docker(
    orchestrator: DiagnosticOrchestrator, fixtures_dir: str
):
    """Verify that dynamic execution is safely rejected and halted when Docker is absent."""
    fixture_path = os.path.join(fixtures_dir, "proj_05")
    repo = Repository(
        id=uuid.uuid4(),
        name="PRJ-005",
        url=f"file:///{fixture_path.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )

    # Request dynamic execution
    report = orchestrator.execute_diagnosis(
        repository=repo,
        request=DiagnosticRunRequest(
            capabilities=["static_inspection", "evidence_collection", "adaptive_probing"],
            allow_dynamic=True,
        ),
    )

    assert "dynamic_verification" in report.unsupported_stages
    assert report.stopping_reason == "further_investigation_unsafe_or_unsupported"
    # Ensure zero untrusted commands executed on host
    assert len(report.executed_probes) == 0


def test_reliability_evaluator_produces_valid_reports():
    """Verify that ReliabilityEvaluator runs across all benchmark scenarios and writes valid reports."""
    evaluator = ReliabilityEvaluator()
    data = evaluator.run_comparison()

    assert data["metrics"]["total_scenarios"] == 60
    assert data["metrics"]["supported_scenarios_count"] == 56
    assert data["metrics"]["healthy_controls_count"] == 34

    # Check adaptive metrics
    ad = data["metrics"]["adaptive"]
    assert ad["top1_accuracy"].numerator == 56
    assert ad["top1_accuracy"].denominator == 56
    assert ad["false_positive_rate"].numerator == 0
    assert ad["multiple_fault_accuracy"].numerator == 8
    assert ad["multiple_fault_accuracy"].denominator == 8
    assert ad["downstream_blocked_accuracy"].numerator == 1
    assert ad["unsafe_probe_rejection"].numerator == 4
    assert ad["repeated_probes_prevented"].percentage == 100.0

    # Ensure reports can be generated on disk
    report_dict = run_and_save_report()
    assert report_dict is not None
