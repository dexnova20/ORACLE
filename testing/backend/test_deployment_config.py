"""Tests for deployment configuration, production invariants, container specifications, and health probes."""

import os
import re
import pytest
from fastapi.testclient import TestClient

from oracle.core.config import Settings
from oracle.main import app


def test_settings_default_environment() -> None:
    """Verify default settings configuration."""
    s = Settings()
    assert s.environment == "development"
    assert s.debug is False
    assert "postgresql+psycopg://" in s.database_url


def test_settings_production_debug_forbidden() -> None:
    """Verify debug mode cannot be enabled in production."""
    with pytest.raises(ValueError, match="debug=True is strictly forbidden in production"):
        Settings(
            environment="production",
            debug=True,
            database_url="postgresql+psycopg://valid_user:strong_password_123@db:5432/oracle_db",
        )


def test_settings_production_default_db_credentials_forbidden() -> None:
    """Verify default development database credentials are rejected in production."""
    with pytest.raises(ValueError, match="cannot use default unhardened database credentials"):
        Settings(
            environment="production",
            debug=False,
            database_url="postgresql+psycopg://postgres:postgres@localhost:5432/oracle_db",
        )


def test_settings_production_wildcard_cors_forbidden() -> None:
    """Verify wildcard CORS origins are rejected in production."""
    with pytest.raises(ValueError, match="Wildcard CORS origins .* are prohibited in production"):
        Settings(
            environment="production",
            debug=False,
            database_url="postgresql+psycopg://oracle_user:strong_production_pw@db:5432/oracle_db",
            cors_origins=["*"],
        )


def test_settings_production_valid_custom_config() -> None:
    """Verify valid hardened configuration passes validation in production."""
    s = Settings(
        environment="production",
        debug=False,
        database_url="postgresql+psycopg://oracle_prod:SuperSecurePass987!@db.internal:5432/oracle_prod_db",
        cors_origins=["https://oracle.company.internal"],
    )
    assert s.environment == "production"
    assert s.debug is False
    assert "SuperSecurePass987!" in s.database_url


def test_settings_decomposed_postgres_fields() -> None:
    """Verify decomposed postgres connection fields properly compose database_url."""
    s = Settings(
        postgres_host="db-cluster.internal",
        postgres_port=5433,
        postgres_user="cluster_user",
        postgres_password="cluster_secret_pw",
        postgres_db="custom_oracle_db",
    )
    assert s.database_url == "postgresql+psycopg://cluster_user:cluster_secret_pw@db-cluster.internal:5433/custom_oracle_db"


def test_dockerfile_backend_hardening() -> None:
    """Verify backend Dockerfiles enforce non-root execution, healthchecks, and polyglot runtimes."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dockerfiles = [
        os.path.join(repo_root, "deploy", "Dockerfile.backend"),
        os.path.join(repo_root, "backend", "Dockerfile"),
    ]

    for df_path in dockerfiles:
        assert os.path.exists(df_path), f"Backend Dockerfile missing: {df_path}"
        with open(df_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Non-root user creation & directive
        assert "groupadd -g 10001 oracle" in content or "useradd -u 10001" in content
        assert "USER oracle:oracle" in content

        # Healthcheck defined
        assert "HEALTHCHECK" in content
        assert "/api/v1/health" in content

        # Polyglot runtimes: OpenJDK, Node.js, TypeScript
        assert "openjdk-17-jdk-headless" in content or "openjdk" in content
        assert "nodejs" in content
        assert "typescript" in content

        # Precompiled Java AST worker
        assert "javac" in content
        assert "JavaAstWorker.java" in content


def test_dockerfile_frontend_hardening() -> None:
    """Verify frontend Dockerfiles enforce multi-stage builds, non-root execution, and standalone packaging."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dockerfiles = [
        os.path.join(repo_root, "deploy", "Dockerfile.frontend"),
        os.path.join(repo_root, "frontend", "Dockerfile"),
    ]

    for df_path in dockerfiles:
        assert os.path.exists(df_path), f"Frontend Dockerfile missing: {df_path}"
        with open(df_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Multi-stage targets
        assert "AS deps" in content
        assert "AS builder" in content
        assert "AS runner" in content

        # Non-root user
        assert "adduser" in content and "nextjs" in content
        assert "USER nextjs" in content

        # Standalone server runner
        assert ".next/standalone" in content
        assert ".next/static" in content
        assert 'CMD ["node", "server.js"]' in content

        # Healthcheck defined
        assert "HEALTHCHECK" in content


def test_docker_compose_security_and_topology() -> None:
    """Verify docker-compose.yml enforces network segregation, persistent volume, and daemon isolation."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    compose_path = os.path.join(repo_root, "deploy", "docker-compose.yml")
    assert os.path.exists(compose_path), "docker-compose.yml missing in deploy/"

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Required services
    assert "db:" in content
    assert "backend:" in content
    assert "frontend:" in content

    # Database service configuration
    assert "postgres:16-alpine" in content
    assert "oracle_pgdata:/var/lib/postgresql/data" in content
    assert "pg_isready" in content

    # Network segregation
    assert "oracle_internal:" in content
    assert "internal: true" in content
    assert "oracle_external:" in content

    # Service dependencies
    assert "service_healthy" in content

    # Security Invariant: No Docker socket volume mount into backend container!
    non_comment_lines = [line.strip() for line in content.splitlines() if not line.strip().startswith("#")]
    assert not any("/var/run/docker.sock" in line for line in non_comment_lines), (
        "CRITICAL SECURITY VIOLATION: Backend container must NOT mount /var/run/docker.sock"
    )


def test_entrypoint_backend_script() -> None:
    """Verify backend entrypoint script enforces error handling, migration, and command chaining."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    entrypoint_path = os.path.join(repo_root, "deploy", "entrypoint-backend.sh")
    assert os.path.exists(entrypoint_path), "deploy/entrypoint-backend.sh missing"

    with open(entrypoint_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "#!/bin/sh" in content
    assert "set -e" in content
    assert "alembic upgrade head" in content
    assert 'exec "$@"' in content


def test_health_and_status_endpoints_contract() -> None:
    """Verify /api/v1/health and /api/v1/status schemas including polyglot parser metadata."""
    client = TestClient(app)

    # Liveness probe
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert health_data["app_name"] == "ORACLE"
    assert "version" in health_data
    assert "environment" in health_data

    # Readiness probe
    status_resp = client.get("/api/v1/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "app" in status_data
    assert "database" in status_data
    assert "persistence_mode" in status_data
    assert "docker_isolation_available" in status_data
    assert "parsers" in status_data

    parsers = status_data["parsers"]
    assert parsers["python"] is True
    assert "typescript" in parsers
    assert "java" in parsers
    assert isinstance(parsers["typescript"], bool)
    assert isinstance(parsers["java"], bool)
