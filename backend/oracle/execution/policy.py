"""Execution policy, security boundaries, and workload profile allowlist for dynamic test execution."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from oracle.schemas.execution import ExecutionState


class IsolationCapability(str, Enum):
    """Container / sandbox isolation mechanisms."""

    DOCKER = "docker"
    GVISOR = "gvisor"
    FAKE_PROVIDER = "fake_provider"
    NONE = "none"


class SecurityPolicyError(Exception):
    """Raised when an execution request violates security policy boundaries."""

    pass


class ProfileNotAllowedError(SecurityPolicyError):
    """Raised when a requested workload profile is not in the approved allowlist."""

    pass


class IsolationUnavailableError(SecurityPolicyError):
    """Raised when container isolation is required but unavailable on the host."""

    pass


class WorkloadProfile(BaseModel):
    """Immutable specification for an approved diagnostic execution workload."""

    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Unique immutable profile identifier (e.g. benchmark-db-probe)")
    name: str = Field(..., description="Human-readable workload name")
    description: str = Field(..., description="Diagnostic intent and scope of the workload")
    command: List[str] = Field(..., description="Pre-approved fixed argument list (zero shell interpolation)")
    allowed_args: List[str] = Field(default_factory=list, description="Permitted optional arguments from an allowlist")
    default_timeout_seconds: int = Field(default=15, ge=1, le=60)
    memory_limit_mb: int = Field(default=256, ge=32, le=1024)
    cpu_cores: float = Field(default=1.0, ge=0.1, le=2.0)
    network_enabled: bool = Field(default=False, description="Whether network access is permitted (default False)")
    allowed_env_keys: List[str] = Field(
        default_factory=list,
        description="Explicit allowlist of permitted environment variable keys",
    )
    required_fixture_file: Optional[str] = Field(
        default=None,
        description="Relative file that must be present in snapshot for this profile to run",
    )


# Immutable registry of ORACLE-approved diagnostic workload profiles.
# Targets and users CANNOT supply arbitrary shell commands or custom executable paths.
WORKLOAD_PROFILES: Dict[str, WorkloadProfile] = {
    "health-probe": WorkloadProfile(
        profile_id="health-probe",
        name="Sandbox Health Verification",
        description="Executes a minimal Python statement to verify container isolation and process limits.",
        command=["python", "-c", "print('ORACLE_SANDBOX_HEALTH_OK')"],
        default_timeout_seconds=5,
        memory_limit_mb=128,
        cpu_cores=0.5,
        network_enabled=False,
    ),
    "benchmark-env-audit": WorkloadProfile(
        profile_id="benchmark-env-audit",
        name="Environment Configuration Audit",
        description="Audits module configuration loading without required environment variables (CASE-005).",
        command=["python", "-c", "import config; config.load_auth_token()"],
        default_timeout_seconds=10,
        memory_limit_mb=256,
        cpu_cores=1.0,
        network_enabled=False,
        required_fixture_file="config.py",
    ),
    "benchmark-db-probe": WorkloadProfile(
        profile_id="benchmark-db-probe",
        name="Database Socket Probing",
        description="Attempts connection to configured database socket, capturing connection refusal (CASE-006).",
        command=["python", "-c", "import db; db.ping_database_socket()"],
        default_timeout_seconds=10,
        memory_limit_mb=256,
        cpu_cores=1.0,
        network_enabled=False,
        required_fixture_file="db.py",
    ),
    "benchmark-contract-check": WorkloadProfile(
        profile_id="benchmark-contract-check",
        name="API Contract Type Assertion",
        description="Evaluates API client payload types against expected contract types (CASE-007).",
        command=[
            "python",
            "-c",
            "import api_client; p = api_client.create_user_payload('abc'); assert isinstance(p['user_id'], int), f\"Contract violation: user_id is {type(p['user_id'])}\"",
        ],
        default_timeout_seconds=10,
        memory_limit_mb=256,
        cpu_cores=1.0,
        network_enabled=False,
        required_fixture_file="api_client.py",
    ),
    "benchmark-transform-test": WorkloadProfile(
        profile_id="benchmark-transform-test",
        name="Data Transformation Runner",
        description="Executes timestamp parsing transformation on sample test input (CASE-008).",
        command=["python", "-c", "import transform; transform.parse_epoch_milliseconds('invalid_epoch_string')"],
        default_timeout_seconds=10,
        memory_limit_mb=256,
        cpu_cores=1.0,
        network_enabled=False,
        required_fixture_file="transform.py",
    ),
}


class ExecutionPolicy(BaseModel):
    """Enforced security constraints for an individual dynamic test execution."""

    model_config = ConfigDict(frozen=True)

    max_timeout_seconds: int = Field(default=30, ge=1, le=60)
    max_output_bytes: int = Field(default=102_400, ge=1024, le=1_048_576)  # 100KB default
    max_memory_mb: int = Field(default=256, ge=32, le=1024)
    max_cpu_cores: float = Field(default=1.0, ge=0.1, le=2.0)
    max_pids: int = Field(default=64, ge=16, le=256)
    network_allowed: bool = Field(default=False)
    read_only_root: bool = Field(default=True)
    read_only_source: bool = Field(default=True)
    no_new_privileges: bool = Field(default=True)
    drop_capabilities: List[str] = Field(default_factory=lambda: ["ALL"])
    allowed_env_vars: Dict[str, str] = Field(default_factory=dict)
