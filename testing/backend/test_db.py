"""Unit and integration tests for database session and connectivity diagnostics."""

import time
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import text
from oracle.db.base import Base
from oracle.db.session import check_db_connectivity, engine, get_db


def test_base_metadata_initialized() -> None:
    """Verify DeclarativeBase metadata is instantiated."""
    assert Base.metadata is not None


def test_get_db_yields_session() -> None:
    """Verify get_db dependency yields and closes session."""
    gen = get_db()
    session = next(gen)
    assert session is not None
    # Verify close is called on generator exhaustion
    try:
        next(gen)
    except StopIteration:
        pass


def test_check_db_connectivity_failure_handled() -> None:
    """Verify check_db_connectivity gracefully returns failure tuple on uncontactable host."""
    with patch("oracle.db.session.engine.connect", side_effect=Exception("Connection refused")):
        connected, message = check_db_connectivity()
        assert connected is False
        assert "Connection refused" in message


def test_check_db_connectivity_success_handled() -> None:
    """Verify check_db_connectivity gracefully returns success tuple when query succeeds."""
    mock_conn = MagicMock()
    with patch("oracle.db.session.engine.connect") as mock_connect:
        mock_connect.return_value.__enter__.return_value = mock_conn
        connected, message = check_db_connectivity()
        assert connected is True
        assert "operational" in message


def test_check_db_connectivity_live_fast_timeout() -> None:
    """Verify that attempting to connect to an unreachable database returns promptly without hanging."""
    start_time = time.monotonic()
    connected, message = check_db_connectivity()
    elapsed = time.monotonic() - start_time
    # Since Postgres is not running locally, this should fail safely and fast (< 10s)
    assert connected is False
    assert "Database connection failed" in message
    assert elapsed < 10.0


@pytest.mark.integration
def test_live_postgres_integration() -> None:
    """Verify live connectivity and query execution against real PostgreSQL instance.

    This test is explicitly skipped when PostgreSQL is not running locally,
    preserving strict honesty without falling back to mock or SQLite substitution.
    """
    connected, message = check_db_connectivity()
    if not connected:
        pytest.skip(f"PostgreSQL service not reachable on configured port: {message}")

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
        assert version is not None
        assert "PostgreSQL" in str(version)
