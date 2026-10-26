"""Comprehensive automated tests for ORACLE evidence-based diagnostic intelligence, ranking, and probe planning."""

from datetime import datetime, timezone
import math
import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient

from ml.planning.probe_planner import (
    DYNAMIC_PROFILE_MAPPING,
    ProbePlanner,
    ProbePlannerConfig,
    calculate_expected_information_gain,
    calculate_shannon_entropy,
)
from ml.ranking.heuristic_ranker import HeuristicRankerConfig, rank_hypotheses
from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.diagnostics.service import DiagnosticOrchestrator
from oracle.main import app
from oracle.models.repository import Repository, RepositoryStatus, SourceType
from oracle.schemas.diagnostics import (
    DiagnosticComponent,
    DiagnosticDependencyEdge,
    DiagnosticEvidenceRecord,
    DiagnosticProbe,
    DiagnosticReport,
    DiagnosticRunRequest,
    DiagnosticSystemMap,
    FaultHypothesis,
    ProbeResult,
)


class MockSession:
    """Mock database session for route testing without live PostgreSQL."""

    def __init__(self) -> None:
        self.store = {}

    def get(self, model, ident):
        return self.store.get(ident)

    def add(self, instance):
        self.store[instance.id] = instance

    def commit(self):
        pass

    def rollback(self):
        pass

    def scalars(self, stmt):
        class Result:
            def first(self):
                return None
            def all(self):
                return []
        return Result()


@pytest.fixture
def mock_db():
    return MockSession()


@pytest.fixture
def client(mock_db: MockSession):
    from oracle.db.session import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def benchmark_fixtures_path() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current_dir, "..", "fixtures", "benchmark"))


# =============================================================================
# 1. Hypothesis Ranking & Heuristic Scoring Tests
# =============================================================================

def test_heuristic_ranker_transparent_scoring():
    """Verify deterministic scoring breakdown, corroboration bonus, and relative score label."""
    evidence = [
        DiagnosticEvidenceRecord(
            evidence_id="EVID-001",
            evidence_type="syntax_error",
            source_component="file:app.py",
            extraction_method="ast_parser",
            reliability="direct_observation",
        ),
        DiagnosticEvidenceRecord(
            evidence_id="EVID-002",
            evidence_type="syntax_error",
            source_component="file:worker.py",
            extraction_method="ast_parser",
            reliability="direct_observation",
        ),
    ]

    h1 = FaultHypothesis(
        hypothesis_id="HYPO-001",
        category=FaultCategory.RUNTIME_EXCEPTION,
        category_title="Runtime Exception",
        affected_component="app.py",
        supporting_evidence_ids=["EVID-001", "EVID-002"],
        verification_status="verified",
    )

    ranked = rank_hypotheses([h1], evidence)
    assert len(ranked) == 1
    top = ranked[0]

    # Expected: Direct obs 1 (35.0) + Add'l evidence (5.0) + Corroboration 2 files (15.0) + Verified (35.0) = 90.0
    assert top.relative_ranking_score == 90.0
    assert top.confidence_level == "high"
    assert "NOT a calibrated probability" in top.score_rationale
    assert "Direct observation" in top.score_rationale
    assert "Independent corroboration" in top.score_rationale


def test_heuristic_ranker_preserves_ambiguity():
    """Verify that when evidence cannot distinguish two hypotheses, their scores remain identical."""
    evidence = [
        DiagnosticEvidenceRecord(
            evidence_id="EVID-IMP-001",
            evidence_type="unresolved_import",
            source_component="file:service.py",
            extraction_method="dependency_graph",
            reliability="direct_observation",
        )
    ]

    h_missing = FaultHypothesis(
        hypothesis_id="HYPO-MISSING",
        category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
        category_title="Dependency Import Failure",
        affected_component="service.py",
        supporting_evidence_ids=["EVID-IMP-001"],
        verification_status="supported",
    )

    h_srcroot = FaultHypothesis(
        hypothesis_id="HYPO-SRCROOT",
        category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
        category_title="Dependency Import Failure",
        affected_component="service.py",
        supporting_evidence_ids=["EVID-IMP-001"],
        verification_status="supported",
    )

    ranked = rank_hypotheses([h_missing, h_srcroot], evidence)
    assert len(ranked) == 2
    # Both share identical supporting evidence and status; scores must be identical
    assert ranked[0].relative_ranking_score == ranked[1].relative_ranking_score
    assert ranked[0].relative_ranking_score == 50.0  # 35 base + 15 supported


def test_heuristic_ranker_deliberate_abstention():
    """Verify that deliberate abstention hypotheses receive 0.0 relative score and 'uncertain' confidence."""
    empty_evid = DiagnosticEvidenceRecord(
        evidence_id="EVID-EMPTY-001",
        evidence_type="empty_codebase",
        source_component="repository_root",
        extraction_method="ast_parser",
        reliability="direct_observation",
    )

    h_abstain = FaultHypothesis(
        hypothesis_id="HYPO-ABSTAIN",
        category=FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE,
        category_title="Unknown / Insufficient Evidence",
        affected_component="repository_root",
        supporting_evidence_ids=["EVID-EMPTY-001"],
        verification_status="unsupported",
        abstention_reason="Empty codebase stub without source files.",
    )

    ranked = rank_hypotheses([h_abstain], [empty_evid])
    assert len(ranked) == 1
    assert ranked[0].relative_ranking_score == 0.0
    assert ranked[0].confidence_level == "uncertain"
    assert ranked[0].verification_status == "insufficient_evidence"
    assert "Deliberate abstention" in ranked[0].score_rationale


# =============================================================================
# 2. Information Theory and Entropy Calculation Tests
# =============================================================================

def test_shannon_entropy_valid_distribution():
    """Verify Shannon entropy calculation on valid normalized distributions."""
    # Uniform distribution over 2 states: H = - (0.5*log2(0.5) + 0.5*log2(0.5)) = 1.0 bit
    h2 = calculate_shannon_entropy([0.5, 0.5])
    assert math.isclose(h2, 1.0, rel_tol=1e-4)

    # Uniform distribution over 4 states: H = 2.0 bits
    h4 = calculate_shannon_entropy([0.25, 0.25, 0.25, 0.25])
    assert math.isclose(h4, 2.0, rel_tol=1e-4)

    # Certainty (one state has prob 1.0): H = 0.0 bits
    h1 = calculate_shannon_entropy([1.0, 0.0])
    assert math.isclose(h1, 0.0, rel_tol=1e-4)


def test_shannon_entropy_invalid_distribution_raises_error():
    """Verify that Shannon entropy calculation rejects unnormalized or invalid distributions."""
    with pytest.raises(ValueError, match="summing to 1.0"):
        calculate_shannon_entropy([0.3, 0.3])  # Sum = 0.6

    with pytest.raises(ValueError, match="non-negative"):
        calculate_shannon_entropy([1.2, -0.2])


def test_expected_information_gain_valid_distribution():
    """Verify Expected Information Gain calculation under valid prior and conditional posteriors."""
    prior = [0.5, 0.5]  # Prior entropy = 1.0 bit

    # Probe outcomes completely resolve the hypothesis: each outcome yields posterior entropy = 0.0
    conditionals = {
        "outcome_A": (0.5, [1.0, 0.0]),
        "outcome_B": (0.5, [0.0, 1.0]),
    }

    eig = calculate_expected_information_gain(prior, conditionals)
    # Expected: EIG = 1.0 - (0.5*0 + 0.5*0) = 1.0 bit
    assert math.isclose(eig, 1.0, rel_tol=1e-4)


def test_expected_information_gain_invalid_outcomes_raises_error():
    """Verify that EIG raises ValueError if outcome probabilities do not sum to 1.0."""
    prior = [0.5, 0.5]
    bad_conditionals = {
        "outcome_A": (0.2, [1.0, 0.0]),
        "outcome_B": (0.3, [0.0, 1.0]),
    }
    with pytest.raises(ValueError, match="Outcome probabilities must sum to 1.0"):
        calculate_expected_information_gain(prior, bad_conditionals)


# =============================================================================
# 3. Probe Planning and Selection Policy Tests
# =============================================================================

def test_candidate_probe_generation():
    """Verify candidate probes generated from hypotheses and system map edges."""
    planner = ProbePlanner()
    hypotheses = [
        FaultHypothesis(
            hypothesis_id="HYPO-001",
            category=FaultCategory.RUNTIME_EXCEPTION,
            category_title="Runtime Exception",
            affected_component="processor.py",
            supporting_evidence_ids=["EVID-SYNTAX-001"],
        ),
        FaultHypothesis(
            hypothesis_id="HYPO-002",
            category=FaultCategory.DEPENDENCY_IMPORT_FAILURE,
            category_title="Dependency Import Failure",
            affected_component="requests, stripe",
            supporting_evidence_ids=["EVID-EXTDEP-001"],
        ),
    ]

    evidence = [
        DiagnosticEvidenceRecord(
            evidence_id="EVID-SYNTAX-001",
            evidence_type="syntax_error",
            source_component="file:processor.py",
            extraction_method="ast_parser",
        ),
        DiagnosticEvidenceRecord(
            evidence_id="EVID-EXTDEP-001",
            evidence_type="undeclared_external_dependency",
            source_component="file:client.py",
            extraction_method="manifest_audit",
        ),
    ]

    sys_map = DiagnosticSystemMap()
    candidates = planner.generate_candidate_probes(
        hypotheses=hypotheses,
        evidence=evidence,
        system_map=sys_map,
        allow_dynamic=False,
        preflight_available=False,
    )

    probe_types = [p.probe_type for p in candidates]
    assert "static_ast_syntax_check" in probe_types
    assert "static_manifest_audit" in probe_types


def test_probe_selection_rejects_unavailable_dynamic_when_docker_absent():
    """Verify dynamic probe is safely rejected when container isolation is absent."""
    planner = ProbePlanner()
    h_config = FaultHypothesis(
        hypothesis_id="HYPO-CFG",
        category=FaultCategory.CONFIG_MISSING_OR_INVALID,
        category_title="Configuration Missing or Invalid",
        affected_component="config.py",
        relative_ranking_score=60.0,
    )

    sys_map = DiagnosticSystemMap()
    # Dynamic enabled by user, but preflight is FALSE (no Docker)
    candidates = planner.generate_candidate_probes(
        hypotheses=[h_config],
        evidence=[],
        system_map=sys_map,
        allow_dynamic=True,
        preflight_available=False,
    )

    assert len(candidates) == 1
    p = candidates[0]
    assert p.requires_dynamic is True
    assert p.availability_status == "unavailable_no_docker"
    assert "Host container runtime unavailable" in p.rejection_reason

    # Selection policy must reject the probe and halt with safe stopping reason
    selected, decision = planner.select_next_probe(
        candidate_probes=candidates,
        hypotheses=[h_config],
        iteration=1,
    )
    assert selected is None
    assert decision.decision_type == "reject_unsafe_probe"
    assert decision.stopping_reason == "further_investigation_unsafe_or_unsupported"
    assert "All remaining candidate probes are unavailable" in decision.rationale


# =============================================================================
# 4. Downstream Dependency-Aware Reasoning Tests
# =============================================================================

def test_downstream_component_independent_check_and_blocked_status(
    client: TestClient,
    mock_db: MockSession,
    benchmark_fixtures_path: str,
):
    """Verify downstream component is evaluated independently and marked 'blocked' rather than faulty."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_11")
    repo = Repository(
        id=uuid.uuid4(),
        name="Downstream Blocked Fixture",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
    assert res.status_code == 200
    report = res.json()

    # Upstream syntax error must be diagnosed
    assert len(report["hypotheses"]) >= 1
    top_hypo = report["hypotheses"][0]
    assert top_hypo["category"] == FaultCategory.RUNTIME_EXCEPTION.value
    assert "upstream.py" in top_hypo["affected_component"]
    assert top_hypo["verification_status"] == "verified"

    # In system map, downstream component must be blocked by upstream
    sys_map = report["system_map"]
    downstream_node = next(
        (c for c in sys_map["components"] if "downstream.py" in c["id"]),
        None,
    )
    assert downstream_node is not None
    # Downstream component is blocked, NOT faulty
    assert downstream_node["status"] == "blocked"

    # Probes executed must include static syntax check
    executed_types = [p["probe_type"] for p in report["executed_probes"]]
    assert "static_ast_syntax_check" in executed_types


# =============================================================================
# 5. REST API Probe & Decision Endpoints Tests
# =============================================================================

def test_api_probes_and_decisions_endpoints(
    client: TestClient,
    mock_db: MockSession,
    benchmark_fixtures_path: str,
):
    """Verify GET /diagnostics/{run_id}/probes and GET /diagnostics/{run_id}/decisions endpoints."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_02")
    repo = Repository(
        id=uuid.uuid4(),
        name="Syntax Error Run",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    # 1. Trigger diagnosis
    diag_res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
    assert diag_res.status_code == 200
    report = diag_res.json()
    run_id = report["run_id"]

    # 2. Query /diagnostics/{run_id}/probes
    probes_res = client.get(f"/api/v1/diagnostics/{run_id}/probes")
    assert probes_res.status_code == 200
    probes_data = probes_res.json()
    assert probes_data["run_id"] == run_id
    assert len(probes_data["executed_probes"]) >= 1
    assert probes_data["executed_probes"][0]["outcome"] == "confirmed"

    # 3. Query /diagnostics/{run_id}/decisions
    dec_res = client.get(f"/api/v1/diagnostics/{run_id}/decisions")
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["run_id"] == run_id
    assert len(dec_data["decisions"]) >= 1
    assert dec_data["decisions"][0]["decision_type"] in ("select_probe", "stop_investigation")
    assert dec_data["stopping_reason"] is not None
