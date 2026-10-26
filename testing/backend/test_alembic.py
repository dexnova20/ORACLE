"""Tests for Alembic migration configuration and offline operations."""

import io
import os
from contextlib import redirect_stdout
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command


def test_alembic_config_and_script_directory() -> None:
    """Verify that Alembic configuration file and script directory load properly."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    ini_path = os.path.join(backend_dir, "alembic.ini")
    assert os.path.exists(ini_path), f"alembic.ini not found at {ini_path}"

    config = Config(ini_path)
    config.set_main_option("script_location", os.path.join(backend_dir, "alembic"))

    script_dir = ScriptDirectory.from_config(config)
    assert script_dir is not None
    assert os.path.exists(script_dir.versions)


def test_alembic_offline_sql_generation_uses_postgresql() -> None:
    """Verify that Alembic runs in offline mode using the configured PostgreSQL dialect."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    ini_path = os.path.join(backend_dir, "alembic.ini")

    config = Config(ini_path)
    config.set_main_option("script_location", os.path.join(backend_dir, "alembic"))

    buf = io.StringIO()
    with redirect_stdout(buf):
        command.upgrade(config, "head", sql=True)

    output = buf.getvalue()
    # Offline mode generates transactional DDL for PostgreSQL
    assert "BEGIN;" in output and "COMMIT;" in output
    assert "CREATE TABLE repositories" in output
    assert "001_create_repositories" in output
