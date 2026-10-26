"""Health and status diagnostic endpoints."""

import time
from typing import List, Optional, Tuple
from fastapi import APIRouter
from pydantic import BaseModel, Field

from oracle.core.config import settings
from oracle.db.session import check_db_connectivity
from oracle.execution.preflight import check_isolation_preflight
from oracle.inspection.ts_parser import check_ts_parser_available
from oracle.inspection.java_parser import check_java_parser_available

router = APIRouter()

# In-memory TTL cache for polyglot parser probes to ensure low-latency status responses
_cached_ts_status: Tuple[bool, Optional[str], float] = (False, None, 0.0)
_cached_java_status: Tuple[bool, Optional[str], float] = (False, None, 0.0)
_PARSER_CACHE_TTL_SECONDS = 30.0


def _get_ts_status() -> Tuple[bool, Optional[str]]:
    global _cached_ts_status
    now = time.time()
    if now - _cached_ts_status[2] > _PARSER_CACHE_TTL_SECONDS:
        avail, err = check_ts_parser_available()
        _cached_ts_status = (avail, err, now)
    return _cached_ts_status[0], _cached_ts_status[1]


def _get_java_status() -> Tuple[bool, Optional[str]]:
    global _cached_java_status
    now = time.time()
    if now - _cached_java_status[2] > _PARSER_CACHE_TTL_SECONDS:
        avail, err = check_java_parser_available()
        _cached_java_status = (avail, err, now)
    return _cached_java_status[0], _cached_java_status[1]


class HealthResponse(BaseModel):
    """Basic health check response schema."""

    status: str = Field(..., description="Service status indicator")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic version")
    environment: str = Field(..., description="Runtime environment")


class DatabaseStatus(BaseModel):
    """Database connectivity status schema."""

    connected: bool = Field(..., description="Whether database is reachable")
    message: str = Field(..., description="Status message or error detail")
    driver: str = Field(..., description="Configured database driver")


class ParsersStatus(BaseModel):
    """Polyglot static AST parser runtime status."""

    python: bool = Field(default=True, description="Python AST parser operational")
    typescript: bool = Field(..., description="TypeScript/JavaScript AST parser operational")
    typescript_error: Optional[str] = Field(default=None, description="TypeScript parser error if unavailable")
    java: bool = Field(..., description="Java AST parser operational")
    java_error: Optional[str] = Field(default=None, description="Java parser error if unavailable")
    go: bool = Field(default=True, description="Go AST parser operational")
    go_error: Optional[str] = Field(default=None, description="Go parser error if unavailable")


class SystemStatusResponse(BaseModel):
    """Detailed system diagnostic status response."""

    app: HealthResponse = Field(..., description="Application core status")
    database: DatabaseStatus = Field(..., description="PostgreSQL database status")
    persistence_mode: str = Field(
        default="in_memory_transient",
        description="Active persistence mode: durable_postgresql or in_memory_transient",
    )
    docker_isolation_available: bool = Field(
        default=False,
        description="Whether container sandbox isolation is operational on the host",
    )
    parsers: Optional[ParsersStatus] = Field(
        default=None,
        description="Polyglot static AST parser operational status",
    )
    supported_languages: List[str] = Field(
        default_factory=lambda: ["python", "typescript", "javascript", "java", "go"],
        description="Supported static analysis languages",
    )
    supported_ecosystems: List[str] = Field(
        default_factory=lambda: ["python", "typescript", "javascript", "java", "go"],
        description="Supported dependency and manifest ecosystems",
    )


@router.get("/health", response_model=HealthResponse, tags=["Diagnostics"])
def get_health() -> HealthResponse:
    """Check application responsiveness.

    Returns:
        HealthResponse: Basic application health metadata.
    """
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )


@router.get("/status", response_model=SystemStatusResponse, tags=["Diagnostics"])
def get_status() -> SystemStatusResponse:
    """Perform a system-wide diagnostic check including database connectivity and isolation status.

    Returns:
        SystemStatusResponse: Status metadata for app, database, isolation, parsers, and capabilities.
    """
    db_connected, db_message = check_db_connectivity()
    persistence_mode = "durable_postgresql" if db_connected else "in_memory_transient"
    preflight = check_isolation_preflight(timeout_seconds=1.0)
    ts_available, ts_err = _get_ts_status()
    java_available, java_err = _get_java_status()

    return SystemStatusResponse(
        app=HealthResponse(
            status="healthy",
            app_name=settings.app_name,
            version=settings.version,
            environment=settings.environment,
        ),
        database=DatabaseStatus(
            connected=db_connected,
            message=db_message,
            driver="postgresql+psycopg",
        ),
        persistence_mode=persistence_mode,
        docker_isolation_available=preflight.is_available,
        parsers=ParsersStatus(
            python=True,
            typescript=ts_available,
            typescript_error=ts_err,
            java=java_available,
            java_error=java_err,
            go=True,
            go_error=None,
        ),
        supported_languages=["python", "typescript", "javascript", "java", "go"],
        supported_ecosystems=["python", "typescript", "javascript", "java", "go"],
    )
