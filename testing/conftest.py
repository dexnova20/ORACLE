"""Shared pytest fixtures for the ORACLE testing suite."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend and ml directories are in sys.path so packages are importable
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml"))
if ml_dir not in sys.path:
    sys.path.insert(0, ml_dir)

from oracle.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Provide a TestClient instance for testing API endpoints."""
    return TestClient(app)
