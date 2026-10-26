"""Automated unit and integration tests for the ORACLE unified diagnostic engine."""

from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
import uuid
import pytest
from fastapi.testclient import TestClient

from ml.taxonomy.fault_taxonomy import FaultCategory
from oracle.db.session import get_db
from oracle.execution import DynamicExecutionWorker
from oracle.execution.provider import ExecutionProvider, RawExecutionResult
from oracle.main import app
from oracle.models.repository import Repository, RepositoryStatus, SourceType
from oracle.schemas.diagnostics import DiagnosticReport, DiagnosticRunRequest


class FakeSession:
    """In-memory session mock simulating SQLAlchemy session for offline unit tests."""

    def __init__(self) -> None:
        self.items: Dict[uuid.UUID, Any] = {}

    def add(self, instance: Any) -> None:
        if not getattr(instance, "id", None):
            instance.id = uuid.uuid4()
        self.items[instance.id] = instance

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, instance: Any) -> None:
        pass

    def scalars(self, stmt: object) -> MagicMock:
        mock = MagicMock()
        mock.all.return_value = list(self.items.values())
        mock.first.return_value = next(iter(self.items.values()), None)
        return mock

    def get(self, model: type, ident: uuid.UUID) -> Optional[Any]:
        return self.items.get(ident)

    def delete(self, instance: Any) -> None:
        if getattr(instance, "id", None) in self.items:
            del self.items[instance.id]


@pytest.fixture
def mock_db() -> FakeSession:
    """Fixture providing an isolated in-memory DB session."""
    session = FakeSession()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def benchmark_fixtures_path() -> str:
    """Return absolute path to benchmark fixtures directory."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(repo_root, "testing", "fixtures", "benchmark")


def test_diagnose_repository_not_found(client: TestClient, mock_db: FakeSession) -> None:
    """Verify that initiating diagnosis for an unknown repository returns 404."""
    unknown_id = uuid.uuid4()
    response = client.post(f"/api/v1/repositories/{unknown_id}/diagnose")
    assert response.status_code == 404
    assert f"Repository '{unknown_id}' not found" in response.json()["detail"]


def test_diagnose_rejects_unapproved_workload_profile(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify that requesting an arbitrary unapproved workload profile is rejected with 400."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_01")
    repo = Repository(
        id=uuid.uuid4(),
        name="Security Test",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    payload = {
        "allow_dynamic": True,
        "workload_profile": "rm -rf / --no-preserve-root",
    }
    res = client.post(f"/api/v1/repositories/{repo.id}/diagnose", json=payload)
    assert res.status_code == 400
    assert "not in the approved allowlist" in res.json()["detail"]


def test_diagnose_clean_control_project(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify that a clean healthy control project produces zero false-positive hypotheses."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_01")
    repo = Repository(
        id=uuid.uuid4(),
        name="Control Project 01",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
    assert res.status_code == 200
    report = res.json()

    assert report["status"] == "completed"
    assert report["repository_id"] == str(repo.id)
    assert len(report["hypotheses"]) == 0  # Zero false positives on healthy code!
    assert "No observable software faults detected" in report["summary"]

    # System map verification
    sys_map = report["system_map"]
    assert sys_map["total_components"] > 0
    comp_names = [c["name"] for c in sys_map["components"]]
    assert "app.py" in comp_names
    assert sys_map["syntax_error_component_count"] == 0
    assert sys_map["unresolved_dependency_count"] == 0

    # Stages verification
    assert "validate_target" in report["completed_stages"]
    assert "acquire_snapshot" in report["completed_stages"]
    assert "static_inspection" in report["completed_stages"]
    assert "build_system_map" in report["completed_stages"]
    assert "collect_evidence" in report["completed_stages"]
    assert "generate_hypotheses" in report["completed_stages"]
    assert "generate_report" in report["completed_stages"]


def test_diagnose_syntax_error_scenario(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify end-to-end diagnosis of syntax error in proj_02."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_02")
    repo = Repository(
        id=uuid.uuid4(),
        name="Syntax Error Fixture",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
    assert res.status_code == 200
    report = res.json()

    assert report["status"] in ("completed", "partial")
    assert len(report["hypotheses"]) >= 1

    top_hypo = report["hypotheses"][0]
    assert top_hypo["category"] == FaultCategory.RUNTIME_EXCEPTION.value
    assert "processor.py" in top_hypo["affected_component"]
    assert top_hypo["confidence_level"] == "high"
    assert top_hypo["verification_status"] == "verified"

    # Evidence records check
    syntax_evids = [e for e in report["evidence"] if e["evidence_type"] == "syntax_error"]
    assert len(syntax_evids) >= 1
    assert syntax_evids[0]["observed_data"]["line_number"] == 6

    # Verification outcome check
    vo = [v for v in report["verification"] if v["hypothesis_id"] == top_hypo["hypothesis_id"]]
    assert len(vo) == 1
    assert vo[0]["status"] == "verified"
    assert vo[0]["method"] == "static_ast_validation"


def test_diagnose_unresolved_internal_import_scenario(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify end-to-end diagnosis of missing internal relative import in proj_03."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_03")
    repo = Repository(
        id=uuid.uuid4(),
        name="Unresolved Import Fixture",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
    assert res.status_code == 200
    report = res.json()

    assert len(report["hypotheses"]) >= 1
    top_hypo = report["hypotheses"][0]
    assert top_hypo["category"] == FaultCategory.DEPENDENCY_IMPORT_FAILURE.value
    assert "service.py" in top_hypo["affected_component"]
    assert top_hypo["verification_status"] == "verified"

    # System map has unresolved node
    sys_map = report["system_map"]
    assert sys_map["unresolved_dependency_count"] >= 1
    unres_nodes = [c for c in sys_map["components"] if c["status"] == "unresolved"]
    assert len(unres_nodes) >= 1


def test_diagnose_undeclared_external_dependencies(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify end-to-end diagnosis of undeclared dependencies in proj_04."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_04")
    repo = Repository(
        id=uuid.uuid4(),
        name="Undeclared Dep Fixture",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
    assert res.status_code == 200
    report = res.json()

    assert len(report["hypotheses"]) >= 1
    top_hypo = report["hypotheses"][0]
    assert top_hypo["category"] == FaultCategory.DEPENDENCY_IMPORT_FAILURE.value
    assert "requests" in top_hypo["affected_component"] or "stripe" in top_hypo["affected_component"]
    assert top_hypo["confidence_level"] == "medium"
    assert top_hypo["verification_status"] == "partially_verified"


def test_diagnose_empty_repository_deliberate_abstention(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify that an empty repository triggers deliberate abstention with UNKNOWN_INSUFFICIENT_EVIDENCE."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_10")
    repo = Repository(
        id=uuid.uuid4(),
        name="Empty Repository Fixture",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
    assert res.status_code == 200
    report = res.json()

    assert len(report["hypotheses"]) == 1
    hypo = report["hypotheses"][0]
    assert hypo["category"] == FaultCategory.UNKNOWN_INSUFFICIENT_EVIDENCE.value
    assert hypo["confidence_level"] == "uncertain"
    assert report["abstention_reason"] is not None
    assert "No parseable Python source files found" in report["abstention_reason"]


def test_diagnose_dynamic_gating_when_isolation_unavailable(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify that when dynamic execution is requested but Docker is missing, it is marked unsupported with no host fallback."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_01")
    repo = Repository(
        id=uuid.uuid4(),
        name="Dynamic Gating Test",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    payload = {"allow_dynamic": True}
    res = client.post(f"/api/v1/repositories/{repo.id}/diagnose", json=payload)
    assert res.status_code == 200
    report = res.json()

    # On Windows host without Docker daemon:
    assert "dynamic_verification" in report["unsupported_stages"]
    dynamic_outcomes = [
        v for v in report["verification"] if v["hypothesis_id"] == "dynamic_verification"
    ]
    assert len(dynamic_outcomes) == 1
    assert dynamic_outcomes[0]["status"] == "unsupported"
    assert "Host execution is strictly forbidden" in dynamic_outcomes[0]["details"]


def test_diagnose_retrieval_endpoints(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify GET /repositories/{id}/diagnostics/latest and GET /diagnostics/{run_id}."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_01")
    repo = Repository(
        id=uuid.uuid4(),
        name="Retrieval Target",
        url=f"file:///{proj_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    # Trigger
    post_res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
    assert post_res.status_code == 200
    report = post_res.json()
    run_id = report["run_id"]

    # Latest by repo
    latest_res = client.get(f"/api/v1/repositories/{repo.id}/diagnostics/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["run_id"] == run_id

    # By run UUID
    run_res = client.get(f"/api/v1/diagnostics/{run_id}")
    assert run_res.status_code == 200
    assert run_res.json()["run_id"] == run_id

    # List runs
    list_res = client.get("/api/v1/diagnostics/runs")
    assert list_res.status_code == 200
    run_ids = [r["run_id"] for r in list_res.json()]
    assert run_id in run_ids

    # Probes endpoint
    probes_res = client.get(f"/api/v1/diagnostics/{run_id}/probes")
    assert probes_res.status_code == 200
    probes_data = probes_res.json()
    assert probes_data["run_id"] == run_id
    assert "candidate_probes" in probes_data
    assert "executed_probes" in probes_data

    # Decisions endpoint
    decisions_res = client.get(f"/api/v1/diagnostics/{run_id}/decisions")
    assert decisions_res.status_code == 200
    decisions_data = decisions_res.json()
    assert decisions_data["run_id"] == run_id
    assert "decisions" in decisions_data
    assert "investigation_history" in decisions_data


def test_diagnose_redacts_sensitive_credentials(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify that credentials in repository URLs are redacted from diagnostic reports."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_01")
    secret_url = f"file:///{proj_dir.replace(os.sep, '/')}?token=super_secret_token_12345"
    repo = Repository(
        id=uuid.uuid4(),
        name="Credential Scrubbing",
        url=secret_url,
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
    assert res.status_code == 200
    report = res.json()
    assert "super_secret_token_12345" not in report["repository_url"]
    assert "super_secret_token_12345" not in str(report)


def test_diagnose_dynamic_verification_with_fake_provider(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify dynamic verification stage when isolation provider is present."""
    from oracle.diagnostics.service import diagnostic_orchestrator
    from oracle.execution.provider import FakeExecutionProvider

    fake_provider = FakeExecutionProvider(
        is_available=True,
        simulated_exit_code=0,
        simulated_stdout="Health probe passed successfully.",
    )
    old_worker = diagnostic_orchestrator.execution_worker
    diagnostic_orchestrator.execution_worker = DynamicExecutionWorker(provider=fake_provider)

    try:
        proj_dir = os.path.join(benchmark_fixtures_path, "proj_01")
        repo = Repository(
            id=uuid.uuid4(),
            name="Dynamic Fake Test",
            url=f"file:///{proj_dir.replace(os.sep, '/')}",
            source_type=SourceType.LOCAL_DIRECTORY.value,
            status=RepositoryStatus.REGISTERED.value,
        )
        mock_db.add(repo)

        payload = {
            "allow_dynamic": True,
            "workload_profile": "health-probe",
        }
        res = client.post(f"/api/v1/repositories/{repo.id}/diagnose", json=payload)
        assert res.status_code == 200
        report = res.json()

        dynamic_outcomes = [
            v for v in report["verification"] if v["hypothesis_id"] == "dynamic_workload"
        ]
        assert len(dynamic_outcomes) == 1
        assert dynamic_outcomes[0]["status"] == "verified"
        assert dynamic_outcomes[0]["workload_profile"] == "health-probe"
        assert dynamic_outcomes[0]["exit_code"] == 0
    finally:
        diagnostic_orchestrator.execution_worker = old_worker

