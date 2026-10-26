"""Isolation providers for sandboxed dynamic test execution."""

from abc import ABC, abstractmethod
import os
import shutil
import subprocess
import tempfile
import time
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from oracle.core.config import settings
from oracle.execution.policy import ExecutionPolicy, WorkloadProfile
from oracle.execution.preflight import PreflightStatus, check_isolation_preflight


class RawExecutionResult(BaseModel):
    """Raw output and metadata captured directly from the isolation provider."""

    model_config = ConfigDict(frozen=True)

    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = Field(default=0.0, ge=0.0)
    timed_out: bool = False
    output_truncated: bool = False
    applied_controls: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class ExecutionProvider(ABC):
    """Abstract interface for sandbox execution providers."""

    @abstractmethod
    def check_preflight(self) -> PreflightStatus:
        """Check whether this execution provider is available on the host."""
        pass

    @abstractmethod
    def execute(
        self,
        profile: WorkloadProfile,
        snapshot_path: str,
        policy: ExecutionPolicy,
    ) -> RawExecutionResult:
        """Execute the approved workload profile inside the sandbox."""
        pass


class DockerExecutionProvider(ExecutionProvider):
    """Production execution provider using Docker containers with hardened security controls."""

    def __init__(
        self,
        docker_bin: Optional[str] = None,
        image: Optional[str] = None,
    ) -> None:
        self.docker_bin = docker_bin or settings.docker_executable
        self.image = image or settings.docker_execution_image

    def check_preflight(self) -> PreflightStatus:
        return check_isolation_preflight(docker_bin=self.docker_bin)

    def build_docker_command(
        self,
        profile: WorkloadProfile,
        snapshot_path: str,
        temp_dir: str,
        policy: ExecutionPolicy,
    ) -> List[str]:
        """Construct the hardened docker run argument list enforcing container isolation."""
        cmd = [
            self.docker_bin,
            "run",
            "--rm",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "-m",
            f"{profile.memory_limit_mb}m",
            "--cpus",
            f"{profile.cpu_cores}",
            "--pids-limit",
            f"{policy.max_pids}",
            "-v",
            f"{os.path.abspath(snapshot_path)}:/workspace:ro",
            "-v",
            f"{temp_dir}:/tmp:rw",
            "-w",
            "/workspace",
        ]

        if not profile.network_enabled:
            cmd.extend(["--network", "none"])

        for k, v in policy.allowed_env_vars.items():
            if k in profile.allowed_env_keys:
                cmd.extend(["-e", f"{k}={v}"])

        cmd.append(self.image)
        cmd.extend(profile.command)
        return cmd

    def execute(
        self,
        profile: WorkloadProfile,
        snapshot_path: str,
        policy: ExecutionPolicy,
    ) -> RawExecutionResult:
        preflight = self.check_preflight()
        if not preflight.is_available:
            return RawExecutionResult(
                exit_code=None,
                duration_ms=0.0,
                timed_out=False,
                output_truncated=False,
                applied_controls=[],
                error_message="; ".join(preflight.missing_reasons),
            )

        timeout = min(profile.default_timeout_seconds, policy.max_timeout_seconds)
        temp_dir = tempfile.mkdtemp(prefix="oracle_worker_tmp_")
        start_time = time.monotonic()

        applied_controls = [
            "docker_container_isolation",
            "read_only_root_fs",
            "read_only_source_mount",
            "cap_drop_all",
            "no_new_privileges",
            "isolated_ephemeral_tmpfs",
            f"memory_limit_{profile.memory_limit_mb}mb",
            f"cpu_limit_{profile.cpu_cores}",
            f"pids_limit_{policy.max_pids}",
        ]
        if not profile.network_enabled:
            applied_controls.append("network_disabled")

        cmd = self.build_docker_command(profile, snapshot_path, temp_dir, policy)

        stdout_data = ""
        stderr_data = ""
        exit_code: Optional[int] = None
        timed_out = False
        output_truncated = False
        error_message: Optional[str] = None

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            exit_code = proc.returncode
            stdout_data = proc.stdout
            stderr_data = proc.stderr

            # Enforce output length limit
            combined_len = len(stdout_data) + len(stderr_data)
            if combined_len > policy.max_output_bytes:
                output_truncated = True
                stdout_data = stdout_data[: policy.max_output_bytes // 2]
                stderr_data = stderr_data[: policy.max_output_bytes // 2]

        except subprocess.TimeoutExpired as te:
            timed_out = True
            error_message = f"Execution exceeded maximum timeout of {timeout}s."
            if te.stdout:
                stdout_data = te.stdout.decode("utf-8", errors="replace") if isinstance(te.stdout, bytes) else te.stdout
            if te.stderr:
                stderr_data = te.stderr.decode("utf-8", errors="replace") if isinstance(te.stderr, bytes) else te.stderr
        except Exception as ex:
            error_message = f"Process invocation error: {str(ex)}"
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except OSError:
                pass

        duration_ms = (time.monotonic() - start_time) * 1000.0

        return RawExecutionResult(
            exit_code=exit_code,
            stdout=stdout_data,
            stderr=stderr_data,
            duration_ms=round(duration_ms, 2),
            timed_out=timed_out,
            output_truncated=output_truncated,
            applied_controls=applied_controls,
            error_message=error_message,
        )


class FakeExecutionProvider(ExecutionProvider):
    """Test double for deterministic unit and security verification without running untrusted code."""

    def __init__(
        self,
        is_available: bool = True,
        simulated_exit_code: int = 0,
        simulated_stdout: str = "",
        simulated_stderr: str = "",
        should_timeout: bool = False,
        should_flood_output: bool = False,
        simulated_duration_ms: float = 12.5,
        applied_controls: Optional[List[str]] = None,
    ) -> None:
        self.is_available = is_available
        self.simulated_exit_code = simulated_exit_code
        self.simulated_stdout = simulated_stdout
        self.simulated_stderr = simulated_stderr
        self.should_timeout = should_timeout
        self.should_flood_output = should_flood_output
        self.simulated_duration_ms = simulated_duration_ms
        self.applied_controls = applied_controls or [
            "mock_sandbox_isolation",
            "read_only_source_mount",
            "no_network",
            "cap_drop_all",
            "no_new_privileges",
        ]
        self.execution_attempts = 0

    def check_preflight(self) -> PreflightStatus:
        if self.is_available:
            return PreflightStatus(
                is_available=True,
                provider="fake_provider",
                missing_reasons=[],
                capabilities=["mock_isolation", "read_only_root", "no_network"],
                details={"mock": True},
            )
        return PreflightStatus(
            is_available=False,
            provider="none",
            missing_reasons=["Fake provider configured as offline for isolation testing."],
            capabilities=[],
            details={"mock": True},
        )

    def execute(
        self,
        profile: WorkloadProfile,
        snapshot_path: str,
        policy: ExecutionPolicy,
    ) -> RawExecutionResult:
        self.execution_attempts += 1

        if not self.is_available:
            return RawExecutionResult(
                exit_code=None,
                duration_ms=0.0,
                timed_out=False,
                output_truncated=False,
                applied_controls=[],
                error_message="Isolation provider unavailable: Fake provider offline.",
            )

        if self.should_timeout:
            return RawExecutionResult(
                exit_code=None,
                stdout="Process started...",
                stderr="",
                duration_ms=float(policy.max_timeout_seconds * 1000.0),
                timed_out=True,
                output_truncated=False,
                applied_controls=self.applied_controls,
                error_message=f"Execution timed out after {policy.max_timeout_seconds}s.",
            )

        stdout = self.simulated_stdout
        stderr = self.simulated_stderr
        output_truncated = False

        if self.should_flood_output:
            flood_bytes = "A" * (policy.max_output_bytes + 2048)
            stdout = flood_bytes[: policy.max_output_bytes // 2]
            stderr = flood_bytes[: policy.max_output_bytes // 2]
            output_truncated = True

        return RawExecutionResult(
            exit_code=self.simulated_exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=self.simulated_duration_ms,
            timed_out=False,
            output_truncated=output_truncated,
            applied_controls=self.applied_controls,
            error_message=None if self.simulated_exit_code == 0 else f"Process exited with non-zero status {self.simulated_exit_code}",
        )
