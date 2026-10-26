"""Execution worker coordinating security policy validation, isolation dispatch, and forensic reporting."""

from datetime import datetime, timezone
import os
from typing import Dict, Optional
import uuid

from oracle.core.config import settings
from oracle.execution.policy import (
    ExecutionPolicy,
    ExecutionState,
    ProfileNotAllowedError,
    WORKLOAD_PROFILES,
    WorkloadProfile,
)
from oracle.execution.provider import (
    DockerExecutionProvider,
    ExecutionProvider,
    RawExecutionResult,
)
from oracle.inspection.policy import redact_secrets
from oracle.models.repository import Repository
from oracle.schemas.execution import ExecutionReport, ExecutionRequest


class DynamicExecutionWorker:
    """Coordinates controlled dynamic test execution within isolated container boundaries."""

    def __init__(self, provider: Optional[ExecutionProvider] = None) -> None:
        self.provider = provider or DockerExecutionProvider()
        # In-memory execution reports storage
        self._reports: Dict[uuid.UUID, ExecutionReport] = {}
        self._latest_by_repo: Dict[uuid.UUID, ExecutionReport] = {}

    def get_report(self, execution_id: uuid.UUID) -> Optional[ExecutionReport]:
        """Retrieve an execution report by execution ID."""
        return self._reports.get(execution_id)

    def get_latest_report(self, repository_id: uuid.UUID) -> Optional[ExecutionReport]:
        """Retrieve the latest execution report for a repository target."""
        return self._latest_by_repo.get(repository_id)

    def execute_workload(
        self,
        repository: Repository,
        request: ExecutionRequest,
        snapshot_path: str,
    ) -> ExecutionReport:
        """Validate execution request, check isolation preflight, and dispatch to provider."""
        execution_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)

        # 1. Validate requested workload profile against immutable allowlist
        if request.profile_id not in WORKLOAD_PROFILES:
            report = ExecutionReport(
                execution_id=execution_id,
                repository_id=repository.id,
                profile_id=request.profile_id,
                status=ExecutionState.REJECTED_BY_POLICY,
                exit_code=None,
                stdout="",
                stderr="",
                output_truncated=False,
                duration_ms=0.0,
                applied_isolation_controls=[],
                termination_reason=f"Workload profile '{request.profile_id}' is not in the approved ORACLE allowlist.",
                error_message="Arbitrary command execution is strictly forbidden.",
                provenance={"worker_version": "1.0.0", "provider": self.provider.__class__.__name__},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            self._save_report(report)
            return report

        profile: WorkloadProfile = WORKLOAD_PROFILES[request.profile_id]

        # 2. Check snapshot filesystem readiness
        if not os.path.exists(snapshot_path):
            report = ExecutionReport(
                execution_id=execution_id,
                repository_id=repository.id,
                profile_id=profile.profile_id,
                status=ExecutionState.FAILED,
                exit_code=None,
                stdout="",
                stderr="",
                output_truncated=False,
                duration_ms=0.0,
                applied_isolation_controls=[],
                termination_reason="Target source snapshot path does not exist on disk.",
                error_message=f"Missing snapshot path: {snapshot_path}",
                provenance={"worker_version": "1.0.0", "provider": self.provider.__class__.__name__},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            self._save_report(report)
            return report

        if profile.required_fixture_file:
            req_file_path = os.path.join(snapshot_path, profile.required_fixture_file)
            if not os.path.exists(req_file_path):
                report = ExecutionReport(
                    execution_id=execution_id,
                    repository_id=repository.id,
                    profile_id=profile.profile_id,
                    status=ExecutionState.FAILED,
                    exit_code=None,
                    stdout="",
                    stderr="",
                    output_truncated=False,
                    duration_ms=0.0,
                    applied_isolation_controls=[],
                    termination_reason=f"Required workload file '{profile.required_fixture_file}' missing from snapshot.",
                    error_message=f"File not found: {profile.required_fixture_file}",
                    provenance={"worker_version": "1.0.0", "provider": self.provider.__class__.__name__},
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                )
                self._save_report(report)
                return report

        # 3. Isolation Preflight Check: Never execute code directly on host
        preflight = self.provider.check_preflight()
        if not preflight.is_available:
            report = ExecutionReport(
                execution_id=execution_id,
                repository_id=repository.id,
                profile_id=profile.profile_id,
                status=ExecutionState.ISOLATION_UNAVAILABLE,
                exit_code=None,
                stdout="",
                stderr="",
                output_truncated=False,
                duration_ms=0.0,
                applied_isolation_controls=[],
                termination_reason="Container sandbox isolation is unavailable on host. Host fallback execution is strictly prohibited.",
                error_message="; ".join(preflight.missing_reasons),
                provenance={
                    "worker_version": "1.0.0",
                    "provider": preflight.provider,
                    "preflight_details": preflight.details,
                },
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            self._save_report(report)
            return report

        # 4. Construct enforced execution policy
        timeout = min(
            request.timeout_seconds or profile.default_timeout_seconds,
            settings.max_execution_timeout_seconds,
        )
        policy = ExecutionPolicy(
            max_timeout_seconds=timeout,
            max_output_bytes=settings.max_execution_output_bytes,
            max_memory_mb=profile.memory_limit_mb,
            max_cpu_cores=profile.cpu_cores,
            network_allowed=profile.network_enabled,
        )

        # 5. Dispatch to provider inside sandbox
        raw: RawExecutionResult = self.provider.execute(
            profile=profile,
            snapshot_path=snapshot_path,
            policy=policy,
        )

        # 6. Determine final lifecycle state
        if raw.timed_out:
            status = ExecutionState.TIMED_OUT
            termination_reason = f"Workload timed out after {timeout}s and was terminated."
        elif raw.output_truncated:
            status = ExecutionState.PARTIAL
            termination_reason = "Execution completed, but output exceeded maximum byte quota and was truncated."
        elif raw.exit_code == 0:
            status = ExecutionState.COMPLETED
            termination_reason = "Workload completed successfully with exit code 0."
        elif raw.exit_code is not None:
            status = ExecutionState.FAILED
            termination_reason = f"Workload process exited with failure status {raw.exit_code}."
        else:
            status = ExecutionState.FAILED
            termination_reason = raw.error_message or "Process terminated abnormally."

        completed_at = datetime.now(timezone.utc)

        report = ExecutionReport(
            execution_id=execution_id,
            repository_id=repository.id,
            profile_id=profile.profile_id,
            status=status,
            exit_code=raw.exit_code,
            stdout=redact_secrets(raw.stdout),
            stderr=redact_secrets(raw.stderr),
            output_truncated=raw.output_truncated,
            duration_ms=raw.duration_ms,
            applied_isolation_controls=raw.applied_controls,
            termination_reason=termination_reason,
            error_message=redact_secrets(raw.error_message) if raw.error_message else None,
            provenance={
                "worker_version": "1.0.0",
                "provider": self.provider.__class__.__name__,
                "timeout_seconds": timeout,
            },
            started_at=started_at,
            completed_at=completed_at,
        )

        self._save_report(report)
        return report

    def _save_report(self, report: ExecutionReport) -> None:
        self._reports[report.execution_id] = report
        self._latest_by_repo[report.repository_id] = report
