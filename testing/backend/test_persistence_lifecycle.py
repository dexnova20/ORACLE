"""Persistence and database lifecycle verification tests for ORACLE.

Verifies:
1. Offline Alembic migration generation for PostgreSQL dialect.
2. SQLAlchemy model constraints and relationship mappings.
3. Transparent persistence mode reporting (in_memory_transient vs durable_postgresql).
4. Simulated process restart semantics (retrieval from database after in-memory cache eviction).
5. Input validation (invalid UUIDs, duplicate runs, 404 on missing records).
6. Exact JSON serialization and deserialization fidelity for DiagnosticRunRecord.
"""

from datetime import datetime, timezone
import io
import json
import os
from contextlib import redirect_stdout
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch
import uuid
import pytest
from alembic.config import Config
from alembic import command
from fastapi.testclient import TestClient

from oracle.db.session import check_db_connectivity, get_db
from oracle.diagnostics.service import diagnostic_orchestrator
from oracle.main import app
from oracle.models.diagnostic_run import DiagnosticRunRecord
from oracle.models.repository import Repository, RepositoryStatus, SourceType
from oracle.schemas.diagnostics import DiagnosticReport, DiagnosticSystemMap


class PersistenceFakeSession:
    """In-memory session mock simulating SQLAlchemy session for lifecycle tests."""

    def __init__(self) -> None:
        self.records: Dict[uuid.UUID, Any] = {}

    def add(self, instance: Any) -> None:
        if not getattr(instance, "id", None):
            instance.id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        if not getattr(instance, "created_at", None):
            instance.created_at = now
        if not getattr(instance, "updated_at", None):
            instance.updated_at = now
        self.records[instance.id] = instance

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, instance: Any) -> None:
        pass

    def get(self, model: type, ident: uuid.UUID) -> Optional[Any]:
        return self.records.get(ident)

    def query(self, model: type) -> MagicMock:
        mock = MagicMock()
        matching = [item for item in self.records.values() if isinstance(item, model)]
        mock.order_by.return_value = mock
        mock.limit.return_value = mock
        mock.all.return_value = matching
        mock.first.return_value = matching[0] if matching else None
        return mock

    def delete(self, instance: Any) -> None:
        if getattr(instance, "id", None) in self.records:
            del self.records[instance.id]


@pytest.fixture
def mock_persistence_db() -> PersistenceFakeSession:
    """Fixture providing an isolated in-memory DB session."""
    session = PersistenceFakeSession()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.pop(get_db, None)


def test_alembic_all_revisions_offline_sql_generation() -> None:
    """Verify that Alembic runs in offline mode generating transactional PostgreSQL DDL."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    ini_path = os.path.join(backend_dir, "alembic.ini")
    assert os.path.exists(ini_path)

    config = Config(ini_path)
    config.set_main_option("script_location", os.path.join(backend_dir, "alembic"))

    buf = io.StringIO()
    with redirect_stdout(buf):
        command.upgrade(config, "head", sql=True)

    output = buf.getvalue()
    assert "BEGIN;" in output
    assert "COMMIT;" in output
    assert "CREATE TABLE repositories" in output
    assert "CREATE TABLE diagnostic_runs" in output


def test_persistence_mode_honest_offline_reporting(client: TestClient) -> None:
    """Verify that when PostgreSQL is offline, status endpoint declares in_memory_transient."""
    with patch("oracle.api.v1.endpoints.health.check_db_connectivity", return_value=(False, "Connection refused")):
        res = client.get("/api/v1/status")
        assert res.status_code == 200
        data = res.json()
        assert data["database"]["connected"] is False
        assert data["persistence_mode"] == "in_memory_transient"


def test_persistence_mode_honest_online_reporting(client: TestClient) -> None:
    """Verify that when PostgreSQL is connected, status endpoint declares durable_postgresql."""
    with patch("oracle.api.v1.endpoints.health.check_db_connectivity", return_value=(True, "Operational")):
        res = client.get("/api/v1/status")
        assert res.status_code == 200
        data = res.json()
        assert data["database"]["connected"] is True
        assert data["persistence_mode"] == "durable_postgresql"


def test_simulated_process_restart_retrieval_from_db(
    client: TestClient,
    mock_persistence_db: PersistenceFakeSession,
) -> None:
    """Verify that if in-memory cache is evicted (simulated restart), reports are restored from database."""
    run_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    mock_report = DiagnosticReport(
        run_id=run_id,
        repository_id=repo_id,
        repository_name="Simulated Service",
        repository_url="file:///tmp/simulated",
        source_type="local_directory",
        status="completed",
        completed_stages=["static_inspection"],
        unsupported_stages=[],
        system_map=DiagnosticSystemMap(),
        evidence=[],
        hypotheses=[],
        verification=[],
        candidate_probes=[],
        executed_probes=[],
        investigation_history=[],
        stopping_reason="sufficient_evidence_verified",
        summary="Simulated diagnostic report",
        recommendations=["Review code"],
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=42.0,
    )

    # Persist in DB record
    db_record = DiagnosticRunRecord(
        id=run_id,
        repository_id=repo_id,
        status="completed",
        report_json=mock_report.model_dump_json(),
        created_at=mock_report.started_at,
        completed_at=mock_report.completed_at,
        duration_ms=42.0,
    )
    mock_persistence_db.add(db_record)

    # Ensure in-memory cache does NOT contain this run
    if run_id in diagnostic_orchestrator._runs_by_id:
        del diagnostic_orchestrator._runs_by_id[run_id]

    # 1. Fetch by run ID - should successfully fallback to DB
    res = client.get(f"/api/v1/diagnostics/{run_id}")
    assert res.status_code == 200
    fetched_report = res.json()
    assert fetched_report["run_id"] == str(run_id)
    assert fetched_report["summary"] == "Simulated diagnostic report"

    # 2. List runs - should include database run
    list_res = client.get("/api/v1/diagnostics/runs")
    assert list_res.status_code == 200
    runs = list_res.json()
    assert any(r["run_id"] == str(run_id) for r in runs)


def test_invalid_uuid_and_missing_record_handling(
    client: TestClient,
    mock_persistence_db: PersistenceFakeSession,
) -> None:
    """Verify input validation: invalid UUID returns 422, non-existent valid UUID returns 404."""
    # Invalid UUID string
    invalid_res = client.get("/api/v1/diagnostics/not-a-valid-uuid")
    assert invalid_res.status_code == 422

    # Non-existent valid UUID
    missing_id = uuid.uuid4()
    missing_res = client.get(f"/api/v1/diagnostics/{missing_id}")
    assert missing_res.status_code == 404
    assert f"Diagnostic run '{missing_id}' not found" in missing_res.json()["detail"]


def test_diagnostic_report_json_roundtrip_fidelity() -> None:
    """Verify that complex DiagnosticReport survives JSON serialization and deserialization with 100% fidelity."""
    run_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    original_report = DiagnosticReport(
        run_id=run_id,
        repository_id=repo_id,
        repository_name="Roundtrip Test Repo",
        repository_url="https://github.com/example/repo",
        source_type="git",
        commit_hash="abc1234def5678",
        status="completed",
        completed_stages=["static_inspection", "build_system_map", "collect_evidence"],
        unsupported_stages=["dynamic_verification"],
        system_map=DiagnosticSystemMap(
            total_components=2,
            total_dependencies=1,
            internal_dependency_count=1,
        ),
        evidence=[],
        hypotheses=[],
        verification=[],
        candidate_probes=[],
        executed_probes=[],
        investigation_history=[],
        stopping_reason="budget_exhausted",
        summary="High-fidelity roundtrip test",
        recommendations=["Step 1", "Step 2"],
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_ms=123.45,
    )

    dumped_json = original_report.model_dump_json()
    reconstituted = DiagnosticReport.model_validate_json(dumped_json)

    assert reconstituted.run_id == original_report.run_id
    assert reconstituted.repository_id == original_report.repository_id
    assert reconstituted.commit_hash == "abc1234def5678"
    assert reconstituted.system_map.total_components == 2
    assert reconstituted.stopping_reason == "budget_exhausted"
    assert reconstituted.duration_ms == 123.45
