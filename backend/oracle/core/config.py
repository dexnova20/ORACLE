"""Application configuration management using Pydantic Settings."""

from typing import List, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core application settings populated from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="ORACLE", description="Application name")
    version: str = Field(default="0.1.0", description="Application semantic version")
    environment: str = Field(default="development", description="Runtime environment")
    debug: bool = Field(default=False, description="Debug mode flag")
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 route prefix")

    # PostgreSQL individual connection parameters (optional, can compose database_url)
    postgres_user: Optional[str] = Field(default=None, description="PostgreSQL username")
    postgres_password: Optional[str] = Field(default=None, description="PostgreSQL password")
    postgres_host: Optional[str] = Field(default=None, description="PostgreSQL hostname")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: Optional[str] = Field(default=None, description="PostgreSQL database name")

    # PostgreSQL connection string using psycopg 3 driver
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/oracle_db",
        description="SQLAlchemy database URL for PostgreSQL using psycopg driver",
    )
    db_echo: bool = Field(
        default=False,
        description="Whether SQLAlchemy should log SQL statements",
    )

    # Allowed CORS origins for frontend integration (Next.js default: 3000)
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed origins for Cross-Origin Resource Sharing",
    )

    # Repository Ingestion and Inspection Limits
    permitted_local_roots: list[str] = Field(
        default=[],
        description="Explicitly permitted filesystem roots for local repository ingestion",
    )
    max_inspection_file_count: int = Field(
        default=1000,
        description="Maximum file count allowed during repository inspection",
    )
    max_inspection_file_size_bytes: int = Field(
        default=1_048_576,  # 1MB
        description="Maximum file size in bytes for an individual source file",
    )
    max_inspection_total_bytes: int = Field(
        default=52_428_800,  # 50MB
        description="Maximum aggregate bytes permitted across all inspected files",
    )
    inspection_timeout_seconds: int = Field(
        default=30,
        description="Execution timeout in seconds for repository snapshot and inspection",
    )

    # Dynamic Test Execution Limits & Sandboxing
    docker_executable: str = Field(
        default="docker",
        description="Path or binary name of the Docker CLI executable",
    )
    default_execution_timeout_seconds: int = Field(
        default=15,
        description="Default execution timeout in seconds for containerized test runs",
    )
    max_execution_timeout_seconds: int = Field(
        default=60,
        description="Maximum allowed timeout in seconds for any dynamic test execution",
    )
    max_execution_output_bytes: int = Field(
        default=102_400,  # 100KB
        description="Maximum total bytes captured from container stdout/stderr combined",
    )
    max_execution_memory_mb: int = Field(
        default=256,
        description="Maximum memory allocation in megabytes for container worker",
    )
    max_execution_cpu_cores: float = Field(
        default=1.0,
        description="Maximum CPU core allocation for container worker",
    )
    docker_execution_image: str = Field(
        default="python:3.11-slim",
        description="Pinned base image for containerized diagnostic test execution",
    )

    # Polyglot Worker Optional Paths
    typescript_path: Optional[str] = Field(
        default=None,
        description="Explicit path to typescript package or module for ts_ast_worker.mjs",
    )
    java_ast_worker_dir: Optional[str] = Field(
        default=None,
        description="Explicit directory containing compiled JavaAstWorker.class",
    )

    @model_validator(mode="after")
    def validate_and_compose(self) -> "Settings":
        """Compose database_url if individual components provided, and validate production invariants."""
        # Compose database_url if individual connection fields provided and database_url is the default
        default_db_url = "postgresql+psycopg://postgres:postgres@localhost:5432/oracle_db"
        if self.postgres_host and self.postgres_user and (self.database_url == default_db_url):
            pw = f":{self.postgres_password}" if self.postgres_password else ""
            db = self.postgres_db or "oracle_db"
            self.database_url = f"postgresql+psycopg://{self.postgres_user}{pw}@{self.postgres_host}:{self.postgres_port}/{db}"

        # Standardize postgresql:// to postgresql+psycopg://
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)

        # Production invariant checks
        if self.environment.lower() == "production":
            if self.debug:
                raise ValueError("debug=True is strictly forbidden in production environment.")
            if "postgres:postgres@localhost" in self.database_url:
                raise ValueError(
                    "Production environment cannot use default unhardened database credentials (postgres:postgres@localhost)."
                )
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origins ('*') are prohibited in production environment.")

        return self


settings = Settings()
