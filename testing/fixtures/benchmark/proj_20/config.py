"""Configuration module with robust environment variable fallback defaults."""
import os

def get_database_timeout() -> int:
    """Retrieve database timeout with fallback default."""
    raw = os.getenv("DATABASE_TIMEOUT", "30")
    try:
        return int(raw)
    except ValueError:
        return 30

def get_service_port() -> int:
    return int(os.getenv("PORT", "8000"))
