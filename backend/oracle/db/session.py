"""Database connection engine and session factory."""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from oracle.core.config import settings

# Engine configuration targeting PostgreSQL via psycopg 3
# connect_timeout ensures fast failure detection when host is unreachable (per address attempt)
engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
    future=True,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 2},
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency generator yielding an active SQLAlchemy session.

    Yields:
        Session: Database session instance.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connectivity() -> tuple[bool, str]:
    """Verify connectivity to the configured PostgreSQL instance.

    Returns:
        tuple[bool, str]: (is_connected, message_or_error)
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection operational."
    except Exception as exc:
        return False, f"Database connection failed: {exc.__class__.__name__}: {str(exc)}"
