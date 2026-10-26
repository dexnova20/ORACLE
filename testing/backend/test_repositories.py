"""Unit and integration tests for repository registration and management endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from oracle.db.session import check_db_connectivity, get_db
from oracle.main import app
from oracle.models.repository import Repository, RepositoryStatus, SourceType


class FakeSession:
    """In-memory session mock simulating SQLAlchemy session for offline unit tests."""

    def __init__(self) -> None:
        self.items: dict[uuid.UUID, Repository] = {}

    def add(self, instance: Repository) -> None:
        if not instance.id:
            instance.id = uuid.uuid4()
        if not getattr(instance, "source_type", None):
            instance.source_type = SourceType.GIT.value
        if not getattr(instance, "status", None):
            instance.status = RepositoryStatus.REGISTERED.value
        now = datetime.now(timezone.utc)
        if not getattr(instance, "created_at", None):
            instance.created_at = now
        if not getattr(instance, "updated_at", None):
            instance.updated_at = now
        self.items[instance.id] = instance

    def commit(self) -> None:
        pass

    def refresh(self, instance: Repository) -> None:
        pass

    def scalars(self, stmt: object) -> MagicMock:
        mock = MagicMock()
        # Return sorted by created_at desc
        sorted_items = sorted(
            self.items.values(), key=lambda r: r.created_at, reverse=True
        )
        mock.all.return_value = sorted_items
        return mock

    def get(self, model: type, ident: uuid.UUID) -> Repository | None:
        return self.items.get(ident)

    def delete(self, instance: Repository) -> None:
        if instance.id in self.items:
            del self.items[instance.id]


@pytest.fixture
def mock_db() -> FakeSession:
    """Provide a fresh in-memory session mock for route testing."""
    session = FakeSession()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.pop(get_db, None)


def test_register_repository_success(client: TestClient, mock_db: FakeSession) -> None:
    """Verify successful repository registration with valid metadata."""
    payload = {
        "name": "ORACLE Core",
        "url": "https://github.com/example/oracle.git",
        "source_type": "git",
    }
    response = client.post("/api/v1/repositories", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "ORACLE Core"
    assert data["url"] == "https://github.com/example/oracle.git"
    assert data["source_type"] == "git"
    assert data["status"] == "registered"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_register_repository_invalid_name(client: TestClient, mock_db: FakeSession) -> None:
    """Verify validation rejection on empty or whitespace-only repository names."""
    # Empty string
    res1 = client.post(
        "/api/v1/repositories",
        json={"name": "", "url": "https://github.com/example/repo.git"},
    )
    assert res1.status_code == 422

    # Whitespace-only string
    res2 = client.post(
        "/api/v1/repositories",
        json={"name": "   ", "url": "https://github.com/example/repo.git"},
    )
    assert res2.status_code == 422


def test_register_repository_invalid_url_scheme(
    client: TestClient, mock_db: FakeSession
) -> None:
    """Verify validation rejection on unsupported or malformed URL schemes."""
    # Unsupported scheme (ftp://)
    res1 = client.post(
        "/api/v1/repositories",
        json={"name": "test-repo", "url": "ftp://example.com/repo.git"},
    )
    assert res1.status_code == 422

    # Missing scheme (raw domain)
    res2 = client.post(
        "/api/v1/repositories",
        json={"name": "test-repo", "url": "github.com/example/repo.git"},
    )
    assert res2.status_code == 422

    # Incomplete scheme only
    res3 = client.post(
        "/api/v1/repositories",
        json={"name": "test-repo", "url": "https://"},
    )
    assert res3.status_code == 422


def test_list_repositories(client: TestClient, mock_db: FakeSession) -> None:
    """Verify listing registered repositories."""
    # Pre-populate two repositories
    repo1 = Repository(name="Repo One", url="https://github.com/example/one.git")
    repo2 = Repository(name="Repo Two", url="https://github.com/example/two.git")
    mock_db.add(repo1)
    mock_db.add(repo2)

    response = client.get("/api/v1/repositories")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    names = [r["name"] for r in items]
    assert "Repo One" in names
    assert "Repo Two" in names


def test_get_repository_by_id(client: TestClient, mock_db: FakeSession) -> None:
    """Verify retrieving a registered repository by its UUID."""
    repo = Repository(name="Target Service", url="https://github.com/example/service.git")
    mock_db.add(repo)

    response = client.get(f"/api/v1/repositories/{repo.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(repo.id)
    assert data["name"] == "Target Service"


def test_get_repository_not_found(client: TestClient, mock_db: FakeSession) -> None:
    """Verify 404 response on querying non-existent repository UUID."""
    missing_id = uuid.uuid4()
    response = client.get(f"/api/v1/repositories/{missing_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_repository_and_repeated_deletion(
    client: TestClient, mock_db: FakeSession
) -> None:
    """Verify successful deletion (204) and subsequent 404 on repeated deletion."""
    repo = Repository(name="Deletable Target", url="https://github.com/example/del.git")
    mock_db.add(repo)

    # First deletion: success
    res1 = client.delete(f"/api/v1/repositories/{repo.id}")
    assert res1.status_code == 204

    # Verification: record is gone
    res_check = client.get(f"/api/v1/repositories/{repo.id}")
    assert res_check.status_code == 404

    # Repeated deletion: returns 404
    res2 = client.delete(f"/api/v1/repositories/{repo.id}")
    assert res2.status_code == 404


def test_database_error_handling(client: TestClient) -> None:
    """Verify proper handling when database commit raises an exception."""
    broken_session = MagicMock()
    broken_session.commit.side_effect = Exception("Database disk full")
    app.dependency_overrides[get_db] = lambda: broken_session

    try:
        with pytest.raises(Exception) as exc_info:
            client.post(
                "/api/v1/repositories",
                json={"name": "Broken", "url": "https://github.com/example/broken.git"},
            )
        assert "Database disk full" in str(exc_info.value)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.integration
def test_live_postgres_repository_persistence(client: TestClient) -> None:
    """Live PostgreSQL integration test for full repository persistence.

    Executed only when PostgreSQL service is reachable.
    """
    connected, message = check_db_connectivity()
    if not connected:
        pytest.skip(f"Live PostgreSQL not reachable: {message}")

    payload = {
        "name": f"Integration Target {uuid.uuid4().hex[:6]}",
        "url": "https://github.com/example/integration.git",
        "source_type": "git",
    }
    create_res = client.post("/api/v1/repositories", json=payload)
    assert create_res.status_code == 201
    repo_id = create_res.json()["id"]

    # Verify retrieval
    get_res = client.get(f"/api/v1/repositories/{repo_id}")
    assert get_res.status_code == 200

    # Cleanup
    del_res = client.delete(f"/api/v1/repositories/{repo_id}")
    assert del_res.status_code == 204
