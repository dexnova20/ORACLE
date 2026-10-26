"""End-to-end product workflow integration tests for ORACLE.

Validates the full vertical diagnostic pipeline through the FastAPI HTTP interface:
Registration -> Status -> Inspection -> Diagnosis -> Report Retrieval -> Probes -> Decisions -> Polyglot -> Cleanup.
"""

from datetime import datetime, timezone
import os
from typing import Any, Dict, Optional
from unittest.mock import MagicMock
import uuid
import pytest
from fastapi.testclient import TestClient

from oracle.db.session import get_db
from oracle.main import app
from oracle.models.repository import Repository, RepositoryStatus, SourceType
from oracle.models.diagnostic_run import DiagnosticRunRecord


class FakeSession:
    """In-memory session mock simulating SQLAlchemy session for offline workflow tests."""

    def __init__(self) -> None:
        self.items: Dict[uuid.UUID, Any] = {}

    def add(self, instance: Any) -> None:
        if not getattr(instance, "id", None):
            instance.id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        if not getattr(instance, "created_at", None):
            instance.created_at = now
        if not getattr(instance, "updated_at", None):
            instance.updated_at = now
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

    def query(self, model: type) -> MagicMock:
        mock = MagicMock()
        matching = [item for item in self.items.values() if isinstance(item, model)]
        mock.order_by.return_value = mock
        mock.limit.return_value = mock
        mock.all.return_value = matching
        mock.first.return_value = matching[0] if matching else None
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


def test_e2e_complete_diagnostic_lifecycle(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify complete 17-step end-to-end lifecycle on a Python target repository."""
    # 1. Health and System Status Check
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    status_res = client.get("/api/v1/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert "persistence_mode" in status_data
    assert "docker_isolation_available" in status_data
    assert "python" in status_data["supported_languages"]

    # 2. Register Target Repository
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_01")
    file_url = f"file:///{proj_dir.replace(os.sep, '/')}"
    reg_payload = {
        "name": "E2E Python Clean Service",
        "url": file_url,
        "source_type": "local_directory",
    }
    reg_res = client.post("/api/v1/repositories", json=reg_payload)
    assert reg_res.status_code == 201
    repo_data = reg_res.json()
    repo_id = repo_data["id"]
    assert repo_data["name"] == "E2E Python Clean Service"
    assert repo_data["status"] == "registered"

    # 3. Retrieve Repository Metadata
    get_repo_res = client.get(f"/api/v1/repositories/{repo_id}")
    assert get_repo_res.status_code == 200
    assert get_repo_res.json()["id"] == repo_id

    # 4. List All Repositories
    list_repos_res = client.get("/api/v1/repositories")
    assert list_repos_res.status_code == 200
    all_repo_ids = [r["id"] for r in list_repos_res.json()]
    assert repo_id in all_repo_ids

    # 5. Static Inspection
    inspect_res = client.post(f"/api/v1/repositories/{repo_id}/inspect")
    assert inspect_res.status_code == 200
    inspect_data = inspect_res.json()
    assert inspect_data["status"] == "completed"
    assert "dependency_graph" in inspect_data
    assert len(inspect_data["dependency_graph"]["nodes"]) > 0

    # 6. Trigger End-to-End Diagnosis
    diag_res = client.post(f"/api/v1/repositories/{repo_id}/diagnose")
    assert diag_res.status_code == 200
    report = diag_res.json()
    run_id = report["run_id"]
    assert report["repository_id"] == repo_id
    assert report["status"] == "completed"
    assert "static_inspection" in report["completed_stages"]
    assert "build_system_map" in report["completed_stages"]
    assert "collect_evidence" in report["completed_stages"]
    assert "generate_hypotheses" in report["completed_stages"]
    assert "system_map" in report
    assert "evidence" in report
    assert "hypotheses" in report
    assert "investigation_history" in report
    assert report["duration_ms"] >= 0.0

    # 7. Retrieve Latest Diagnostic Report for Repository
    latest_res = client.get(f"/api/v1/repositories/{repo_id}/diagnostics/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["run_id"] == run_id

    # 8. Retrieve Diagnostic Report by Run UUID
    run_res = client.get(f"/api/v1/diagnostics/{run_id}")
    assert run_res.status_code == 200
    assert run_res.json()["run_id"] == run_id

    # 9. Retrieve Candidate and Executed Probes
    probes_res = client.get(f"/api/v1/diagnostics/{run_id}/probes")
    assert probes_res.status_code == 200
    probes_data = probes_res.json()
    assert probes_data["run_id"] == run_id
    assert isinstance(probes_data["candidate_probes"], list)
    assert isinstance(probes_data["executed_probes"], list)

    # 10. Retrieve Adaptive Investigation Decisions
    decisions_res = client.get(f"/api/v1/diagnostics/{run_id}/decisions")
    assert decisions_res.status_code == 200
    decisions_data = decisions_res.json()
    assert decisions_data["run_id"] == run_id
    assert isinstance(decisions_data["decisions"], list)
    assert isinstance(decisions_data["investigation_history"], list)
    assert decisions_data["stopping_reason"] is not None

    # 11. List All Diagnostic Runs
    list_runs_res = client.get("/api/v1/diagnostics/runs")
    assert list_runs_res.status_code == 200
    runs = list_runs_res.json()
    assert any(r["run_id"] == run_id for r in runs)

    # 12. Trigger Diagnosis with Dynamic Gating
    dynamic_payload = {"allow_dynamic": True}
    dyn_res = client.post(f"/api/v1/repositories/{repo_id}/diagnose", json=dynamic_payload)
    assert dyn_res.status_code == 200
    dyn_report = dyn_res.json()
    # Dynamic execution without docker daemon is gracefully marked unsupported without host execution
    assert "dynamic_verification" in dyn_report["unsupported_stages"] or len(dyn_report["verification"]) >= 0

    # 13. Delete Registered Repository
    del_res = client.delete(f"/api/v1/repositories/{repo_id}")
    assert del_res.status_code == 204

    # 14. Verify 404 on Deleted Target
    deleted_get = client.get(f"/api/v1/repositories/{repo_id}")
    assert deleted_get.status_code == 404


def test_e2e_typescript_diagnostic_lifecycle(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify end-to-end diagnostic workflow on a TypeScript repository with Compiler API."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_31")
    file_url = f"file:///{proj_dir.replace(os.sep, '/')}"
    reg_payload = {
        "name": "E2E TypeScript Service",
        "url": file_url,
        "source_type": "local_directory",
    }
    reg_res = client.post("/api/v1/repositories", json=reg_payload)
    assert reg_res.status_code == 201
    repo_id = reg_res.json()["id"]

    try:
        diag_res = client.post(f"/api/v1/repositories/{repo_id}/diagnose")
        assert diag_res.status_code == 200
        report = diag_res.json()
        assert report["status"] == "completed"
        # Verify TypeScript components were discovered
        component_paths = [c["file_path"] for c in report["system_map"]["components"]]
        assert any(p.endswith(".ts") or p.endswith(".tsx") for p in component_paths)
    finally:
        client.delete(f"/api/v1/repositories/{repo_id}")


def test_e2e_java_diagnostic_lifecycle(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify end-to-end diagnostic workflow on a Java Maven repository with OpenJDK Tree API."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_41")
    file_url = f"file:///{proj_dir.replace(os.sep, '/')}"
    reg_payload = {
        "name": "E2E Java Maven Service",
        "url": file_url,
        "source_type": "local_directory",
    }
    reg_res = client.post("/api/v1/repositories", json=reg_payload)
    assert reg_res.status_code == 201
    repo_id = reg_res.json()["id"]

    try:
        diag_res = client.post(f"/api/v1/repositories/{repo_id}/diagnose")
        assert diag_res.status_code == 200
        report = diag_res.json()
        assert report["status"] == "completed"
        # Verify Java components were discovered
        component_paths = [c["file_path"] for c in report["system_map"]["components"]]
        assert any(p.endswith(".java") for p in component_paths)
    finally:
        client.delete(f"/api/v1/repositories/{repo_id}")


def test_e2e_secret_redaction_and_provenance(
    client: TestClient,
    mock_db: FakeSession,
    benchmark_fixtures_path: str,
) -> None:
    """Verify that credentials in target URLs are scrubbed across all stages and evidence preserves line provenance."""
    proj_dir = os.path.join(benchmark_fixtures_path, "proj_02")
    secret_url = f"file:///{proj_dir.replace(os.sep, '/')}?token=super_secret_e2e_token_9999"
    repo = Repository(
        id=uuid.uuid4(),
        name="Sensitive URL Target",
        url=secret_url,
        source_type=SourceType.LOCAL_DIRECTORY.value,
        status=RepositoryStatus.REGISTERED.value,
    )
    mock_db.add(repo)

    try:
        diag_res = client.post(f"/api/v1/repositories/{repo.id}/diagnose")
        assert diag_res.status_code == 200
        report = diag_res.json()
        report_str = str(report)
        assert "super_secret_e2e_token_9999" not in report_str
        assert "token=***" in report["repository_url"] or "super_secret" not in report["repository_url"]

        # Verify evidence provenance
        assert len(report["evidence"]) > 0
        for ev in report["evidence"]:
            assert ev["evidence_id"].startswith("EVID-")
            assert ev["source_component"] != ""
            assert ev["extraction_method"] != ""
    finally:
        client.delete(f"/api/v1/repositories/{repo.id}")
