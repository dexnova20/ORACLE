"""Comprehensive automated unit, security, and API tests for sandboxed dynamic test execution."""

import os
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient

from oracle.api.v1.endpoints.execution import get_execution_worker
from oracle.core.config import settings
from oracle.db.session import get_db
from oracle.execution import (
    DockerExecutionProvider,
    DynamicExecutionWorker,
    ExecutionPolicy,
    ExecutionState,
    FakeExecutionProvider,
    WORKLOAD_PROFILES,
    check_isolation_preflight,
)
from oracle.main import app
from oracle.models.repository import Repository, SourceType
from oracle.schemas.execution import ExecutionReport, ExecutionRequest


class FakeDbSession:
    """Mock database session for repository lookup in execution endpoint tests."""

    def __init__(self, repositories: list[Repository]):
        self.repositories = {r.id: r for r in repositories}

    def query(self, model):
        session = self

        class Query:
            def filter(self, *expressions):
                return self

            def first(self):
                # Return first repository from the mock map
                return next(iter(session.repositories.values()), None)

        return Query()


@pytest.fixture
def clean_snapshot_dir():
    """Create a clean temporary directory with fixture files."""
    with tempfile.TemporaryDirectory(prefix="test_snap_") as tmp_dir:
        # Create minimal python files for profiles
        with open(os.path.join(tmp_dir, "db.py"), "w", encoding="utf-8") as f:
            f.write("def ping_database_socket(): pass\n")
        with open(os.path.join(tmp_dir, "config.py"), "w", encoding="utf-8") as f:
            f.write("def load_auth_token(): pass\n")
        yield tmp_dir


@pytest.fixture
def sample_repo(clean_snapshot_dir):
    """Provide a sample Repository instance targeting the clean snapshot."""
    return Repository(
        id=uuid.uuid4(),
        name="TargetRepo",
        url=f"file:///{clean_snapshot_dir.replace(os.sep, '/')}",
        source_type=SourceType.LOCAL_DIRECTORY,
    )


def test_workload_profile_allowlist_validation(sample_repo, clean_snapshot_dir):
    """Verify that only approved profiles run and arbitrary commands are rejected."""
    worker = DynamicExecutionWorker(provider=FakeExecutionProvider(is_available=True))

    # 1. Approved profile is accepted
    valid_req = ExecutionRequest(profile_id="health-probe")
    report = worker.execute_workload(sample_repo, valid_req, clean_snapshot_dir)
    assert report.status == ExecutionState.COMPLETED
    assert report.profile_id == "health-probe"

    # 2. Unknown or injected profile is rejected by policy
    malicious_req = ExecutionRequest(profile_id="bash -c 'rm -rf /'")
    report_rejected = worker.execute_workload(sample_repo, malicious_req, clean_snapshot_dir)
    assert report_rejected.status == ExecutionState.REJECTED_BY_POLICY
    assert report_rejected.exit_code is None
    assert "approved oracle allowlist" in report_rejected.termination_reason.lower()


def test_isolation_preflight_reports_unavailable_when_docker_missing():
    """Verify preflight correctly reports unavailability when Docker binary is absent."""
    status = check_isolation_preflight(docker_bin="non_existent_docker_cli_abc123")
    assert status.is_available is False
    assert status.provider == "none"
    assert any("not found in system path" in r.lower() for r in status.missing_reasons)


def test_worker_returns_isolation_unavailable_when_preflight_fails(sample_repo, clean_snapshot_dir):
    """Verify worker returns ISOLATION_UNAVAILABLE without running code when preflight fails."""
    offline_provider = FakeExecutionProvider(is_available=False)
    worker = DynamicExecutionWorker(provider=offline_provider)

    req = ExecutionRequest(profile_id="health-probe")
    report = worker.execute_workload(sample_repo, req, clean_snapshot_dir)

    assert report.status == ExecutionState.ISOLATION_UNAVAILABLE
    assert report.exit_code is None
    assert "host fallback execution is strictly prohibited" in report.termination_reason.lower()
    assert offline_provider.execution_attempts == 0  # Zero execution attempts made!


def test_worker_successful_execution_with_fake_provider(sample_repo, clean_snapshot_dir):
    """Verify worker handles successful container execution and records controls."""
    fake_provider = FakeExecutionProvider(
        is_available=True,
        simulated_exit_code=0,
        simulated_stdout="ORACLE_SANDBOX_HEALTH_OK\n",
    )
    worker = DynamicExecutionWorker(provider=fake_provider)

    req = ExecutionRequest(profile_id="health-probe")
    report = worker.execute_workload(sample_repo, req, clean_snapshot_dir)

    assert report.status == ExecutionState.COMPLETED
    assert report.exit_code == 0
    assert "ORACLE_SANDBOX_HEALTH_OK" in report.stdout
    assert len(report.applied_isolation_controls) > 0
    assert fake_provider.execution_attempts == 1


def test_worker_handles_non_zero_exit_code(sample_repo, clean_snapshot_dir):
    """Verify worker correctly captures non-zero failure exit codes and stderr."""
    fake_provider = FakeExecutionProvider(
        is_available=True,
        simulated_exit_code=1,
        simulated_stderr="KeyError: 'AUTH_SECRET_KEY_MANDATORY'",
    )
    worker = DynamicExecutionWorker(provider=fake_provider)

    req = ExecutionRequest(profile_id="benchmark-env-audit")
    report = worker.execute_workload(sample_repo, req, clean_snapshot_dir)

    assert report.status == ExecutionState.FAILED
    assert report.exit_code == 1
    assert "KeyError" in report.stderr
    assert "exited with failure status 1" in report.termination_reason


def test_worker_handles_timeout_enforcement(sample_repo, clean_snapshot_dir):
    """Verify worker properly captures timeout termination."""
    fake_provider = FakeExecutionProvider(
        is_available=True,
        should_timeout=True,
    )
    worker = DynamicExecutionWorker(provider=fake_provider)

    req = ExecutionRequest(profile_id="health-probe")
    report = worker.execute_workload(sample_repo, req, clean_snapshot_dir)

    assert report.status == ExecutionState.TIMED_OUT
    assert report.exit_code is None
    assert "timed out after" in report.termination_reason.lower()


def test_worker_output_capping_and_truncation(sample_repo, clean_snapshot_dir):
    """Verify that excessive stdout/stderr is capped at maximum output bytes."""
    fake_provider = FakeExecutionProvider(
        is_available=True,
        should_flood_output=True,
    )
    worker = DynamicExecutionWorker(provider=fake_provider)

    req = ExecutionRequest(profile_id="health-probe")
    report = worker.execute_workload(sample_repo, req, clean_snapshot_dir)

    assert report.status == ExecutionState.PARTIAL
    assert report.output_truncated is True
    assert "truncated" in report.termination_reason.lower()
    assert len(report.stdout) <= settings.max_execution_output_bytes


def test_worker_secret_redaction(sample_repo, clean_snapshot_dir):
    """Verify that sensitive access tokens and database credentials are redacted from outputs."""
    raw_leak = (
        "Connected to postgresql://admin:super_secret_password_123@localhost:5432/prod_db "
        "using authorization token ghp_A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8"
    )
    fake_provider = FakeExecutionProvider(
        is_available=True,
        simulated_stdout=raw_leak,
    )
    worker = DynamicExecutionWorker(provider=fake_provider)

    req = ExecutionRequest(profile_id="health-probe")
    report = worker.execute_workload(sample_repo, req, clean_snapshot_dir)

    assert "super_secret_password_123" not in report.stdout
    assert "ghp_A1B2C3D4E5F6" not in report.stdout
    assert "[REDACTED]" in report.stdout


def test_worker_missing_required_fixture_file(sample_repo):
    """Verify execution fails early if a required profile file is missing from snapshot."""
    worker = DynamicExecutionWorker(provider=FakeExecutionProvider(is_available=True))

    with tempfile.TemporaryDirectory(prefix="empty_snap_") as empty_dir:
        req = ExecutionRequest(profile_id="benchmark-db-probe")  # Requires db.py
        report = worker.execute_workload(sample_repo, req, empty_dir)

        assert report.status == ExecutionState.FAILED
        assert "db.py" in report.termination_reason
        assert "not found" in report.error_message.lower()


def test_docker_command_construction_and_hardened_flags(sample_repo, clean_snapshot_dir):
    """Verify Docker command string construction embeds required security flags."""
    provider = DockerExecutionProvider()
    profile = WORKLOAD_PROFILES["health-probe"]
    policy = ExecutionPolicy()

    # Test argument list construction directly
    cmd = provider.build_docker_command(profile, clean_snapshot_dir, "/mock/temp", policy)
    assert "--read-only" in cmd
    assert "--network" in cmd and "none" in cmd
    assert "--cap-drop" in cmd and "ALL" in cmd
    assert "--security-opt" in cmd and "no-new-privileges" in cmd
    assert any("/workspace:ro" in arg for arg in cmd)
    assert any("/tmp:rw" in arg for arg in cmd)

    # When preflight fails in this environment, execute returns safely with error explanation
    result = provider.execute(profile, clean_snapshot_dir, policy)
    assert result.exit_code is None
    assert "not found" in result.error_message.lower() or "disabled" in result.error_message.lower()


def test_api_system_isolation_endpoint():
    """Verify GET /api/v1/system/isolation returns PreflightStatus."""
    client = TestClient(app)
    response = client.get("/api/v1/system/isolation")

    assert response.status_code == 200
    data = response.json()
    assert "is_available" in data
    assert "provider" in data
    assert "missing_reasons" in data
    assert "capabilities" in data


def test_api_execute_endpoint_success_with_mock_worker(sample_repo):
    """Verify POST /api/v1/repositories/{id}/execute returns 200 OK with ExecutionReport."""
    client = TestClient(app)
    fake_worker = DynamicExecutionWorker(
        provider=FakeExecutionProvider(is_available=True, simulated_exit_code=0, simulated_stdout="PROBE_OK\n")
    )

    app.dependency_overrides[get_db] = lambda: FakeDbSession([sample_repo])
    app.dependency_overrides[get_execution_worker] = lambda: fake_worker

    try:
        response = client.post(
            f"/api/v1/repositories/{sample_repo.id}/execute",
            json={"profile_id": "health-probe"},
        )
        assert response.status_code == 200
        report = response.json()
        assert report["profile_id"] == "health-probe"
        assert report["status"] == "completed"
        assert report["stdout"] == "PROBE_OK\n"
    finally:
        app.dependency_overrides.clear()


def test_api_execute_endpoint_rejects_arbitrary_profile(sample_repo):
    """Verify POST /api/v1/repositories/{id}/execute returns 400 Bad Request for arbitrary profiles."""
    client = TestClient(app)
    app.dependency_overrides[get_db] = lambda: FakeDbSession([sample_repo])

    try:
        response = client.post(
            f"/api/v1/repositories/{sample_repo.id}/execute",
            json={"profile_id": "arbitrary_custom_command; whoami"},
        )
        assert response.status_code == 400
        assert "not permitted" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_api_get_latest_execution_report(sample_repo):
    """Verify GET /api/v1/repositories/{id}/execution retrieves latest report."""
    client = TestClient(app)
    fake_worker = DynamicExecutionWorker(
        provider=FakeExecutionProvider(is_available=True, simulated_exit_code=0)
    )

    app.dependency_overrides[get_db] = lambda: FakeDbSession([sample_repo])
    app.dependency_overrides[get_execution_worker] = lambda: fake_worker

    try:
        # Initially 404 (not yet executed)
        r404 = client.get(f"/api/v1/repositories/{sample_repo.id}/execution")
        assert r404.status_code == 404

        # Execute
        client.post(
            f"/api/v1/repositories/{sample_repo.id}/execute",
            json={"profile_id": "health-probe"},
        )

        # Now 200 OK
        r200 = client.get(f"/api/v1/repositories/{sample_repo.id}/execution")
        assert r200.status_code == 200
        assert r200.json()["profile_id"] == "health-probe"
    finally:
        app.dependency_overrides.clear()


def test_benchmark_runner_dynamic_execution_with_fake_provider():
    """Verify BenchmarkRunner dynamic path using FakeExecutionProvider correctly confirms defects."""
    from ml.benchmark.runner import BenchmarkRunner

    # Simulate connection refused for database probe CASE-006
    fake_provider = FakeExecutionProvider(
        is_available=True,
        simulated_exit_code=1,
        simulated_stderr="ConnectionRefusedError: [Errno 111] Connection refused on 127.0.0.1:59999",
    )
    worker = DynamicExecutionWorker(provider=fake_provider)

    runner = BenchmarkRunner(
        execution_worker=worker,
        enable_dynamic=True,
    )

    scenario_case_006 = next(s for s in runner.scenarios if s.scenario_id == "CASE-006")
    res = runner.evaluate_scenario(scenario_case_006)

    # Dynamic execution ran and diagnosed database_connectivity_schema!
    assert res.observed_fault_category == "database_connectivity_schema"
    assert res.evaluation_outcome == "correct"
    assert "database_connectivity_schema" in res.explanation
