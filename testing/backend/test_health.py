"""Integration tests for application health and status endpoints."""

from unittest.mock import patch
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient) -> None:
    """Verify root metadata endpoint returns application info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ORACLE"
    assert data["version"] == "0.1.0"
    assert data["api_v1"] == "/api/v1"


def test_health_endpoint(client: TestClient) -> None:
    """Verify /api/v1/health endpoint returns status ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "ORACLE"
    assert "version" in data
    assert "environment" in data


def test_status_endpoint_with_mocked_db_success(client: TestClient) -> None:
    """Verify /api/v1/status endpoint when database is connected."""
    with patch("oracle.api.v1.endpoints.health.check_db_connectivity", return_value=(True, "Operational")):
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["app"]["status"] == "healthy"
        assert data["database"]["connected"] is True
        assert data["database"]["driver"] == "postgresql+psycopg"
        assert data["database"]["message"] == "Operational"
        assert data["persistence_mode"] == "durable_postgresql"
        assert "docker_isolation_available" in data
        assert "python" in data["supported_languages"]
        assert "typescript" in data["supported_languages"]
        assert "java" in data["supported_languages"]


def test_status_endpoint_with_mocked_db_failure(client: TestClient) -> None:
    """Verify /api/v1/status endpoint when database is unreachable."""
    with patch(
        "oracle.api.v1.endpoints.health.check_db_connectivity",
        return_value=(False, "Database connection failed: Timeout"),
    ):
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["app"]["status"] == "healthy"
        assert data["database"]["connected"] is False
        assert "Timeout" in data["database"]["message"]
        assert data["persistence_mode"] == "in_memory_transient"
