"""Unit tests for configuration management."""

from oracle.core.config import Settings


def test_default_settings() -> None:
    """Verify default configuration values."""
    settings = Settings()
    assert settings.app_name == "ORACLE"
    assert settings.version == "0.1.0"
    assert settings.environment in ("development", "test", "production")
    assert "postgresql+psycopg" in settings.database_url
    assert settings.api_v1_prefix == "/api/v1"


def test_custom_settings_override() -> None:
    """Verify settings can be overridden via arguments or environment."""
    custom_settings = Settings(
        app_name="ORACLE-Test",
        environment="test",
        database_url="postgresql+psycopg://user:pass@test-host:5432/test_db",
    )
    assert custom_settings.app_name == "ORACLE-Test"
    assert custom_settings.environment == "test"
    assert custom_settings.database_url == "postgresql+psycopg://user:pass@test-host:5432/test_db"
