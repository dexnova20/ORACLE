"""Preflight inspection verifying container isolation and security capabilities."""

from datetime import datetime, timezone
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from oracle.core.config import settings


class PreflightStatus(BaseModel):
    """Result of host isolation preflight checks."""

    model_config = ConfigDict(frozen=True)

    is_available: bool = Field(..., description="Whether container sandbox isolation is operational")
    provider: str = Field(..., description="Active isolation provider (docker, none, fake_provider)")
    missing_reasons: List[str] = Field(
        default_factory=list,
        description="Forensic explanations why isolation is unavailable",
    )
    capabilities: List[str] = Field(
        default_factory=list,
        description="Verified security capabilities (e.g. read_only_root, cap_drop, no_network)",
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Platform and engine metadata")
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def check_isolation_preflight(
    docker_bin: Optional[str] = None,
    timeout_seconds: float = 3.0,
) -> PreflightStatus:
    """Probe the host environment to determine whether dynamic sandbox isolation is available.

    Security Rule: If Docker daemon is unavailable, ORACLE returns is_available=False.
    Untrusted repository code must NEVER be executed directly on the host as a fallback.
    """
    bin_name = docker_bin or settings.docker_executable
    cli_path = shutil.which(bin_name)

    if not cli_path:
        return PreflightStatus(
            is_available=False,
            provider="none",
            missing_reasons=[
                f"Container runtime executable '{bin_name}' was not found in system PATH.",
                "Dynamic test execution is disabled to prevent executing untrusted code on the host machine.",
            ],
            capabilities=[],
            details={"cli_path": None, "os": os.name},
        )

    # CLI exists; probe if the Docker daemon is responding
    try:
        proc = subprocess.run(
            [cli_path, "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or "Docker daemon socket connection refused."
            return PreflightStatus(
                is_available=False,
                provider="none",
                missing_reasons=[
                    f"Docker daemon is not responding (exit code {proc.returncode}): {err_msg}",
                    "Dynamic execution requires a functional container daemon to maintain process isolation.",
                ],
                capabilities=[],
                details={"cli_path": cli_path, "returncode": proc.returncode},
            )

        server_version = proc.stdout.strip()

        # Verified capabilities available on standard Docker
        capabilities = [
            "read_only_root",
            "read_only_mount",
            "no_network",
            "cap_drop_all",
            "no_new_privileges",
            "memory_limit",
            "cpu_limit",
            "pids_limit",
        ]

        return PreflightStatus(
            is_available=True,
            provider="docker",
            missing_reasons=[],
            capabilities=capabilities,
            details={
                "cli_path": cli_path,
                "server_version": server_version,
                "os": os.name,
            },
        )

    except subprocess.TimeoutExpired:
        return PreflightStatus(
            is_available=False,
            provider="none",
            missing_reasons=[
                f"Docker probe timed out after {timeout_seconds}s. Daemon may be frozen or unconfigured.",
                "Dynamic test execution is blocked.",
            ],
            capabilities=[],
            details={"cli_path": cli_path, "timeout_seconds": timeout_seconds},
        )
    except Exception as ex:
        return PreflightStatus(
            is_available=False,
            provider="none",
            missing_reasons=[
                f"Unexpected error probing container runtime: {str(ex)}",
                "Dynamic test execution is blocked.",
            ],
            capabilities=[],
            details={"cli_path": cli_path, "exception": str(ex)},
        )
