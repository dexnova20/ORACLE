"""REST API endpoints for sandboxed dynamic test execution and isolation preflight."""

import os
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from oracle.core.config import settings
from oracle.db.session import get_db
from oracle.execution.policy import WORKLOAD_PROFILES, ExecutionState
from oracle.execution.preflight import PreflightStatus, check_isolation_preflight
from oracle.execution.worker import DynamicExecutionWorker
from oracle.inspection.snapshot import SnapshotContext, ingest_git_repository, ingest_local_directory
from oracle.models.repository import Repository
from oracle.schemas.execution import ExecutionReport, ExecutionRequest

router = APIRouter()

# Shared worker instance with in-memory execution report caching
_execution_worker: Optional[DynamicExecutionWorker] = None


def get_execution_worker() -> DynamicExecutionWorker:
    """Dependency provider for DynamicExecutionWorker."""
    global _execution_worker
    if _execution_worker is None:
        _execution_worker = DynamicExecutionWorker()
    return _execution_worker


@router.get(
    "/system/isolation",
    response_model=PreflightStatus,
    summary="Probe host container sandbox isolation capabilities",
)
def get_isolation_status() -> PreflightStatus:
    """Return host container isolation preflight status and security capabilities."""
    return check_isolation_preflight()


@router.post(
    "/repositories/{repository_id}/execute",
    response_model=ExecutionReport,
    status_code=status.HTTP_200_OK,
    summary="Trigger controlled dynamic workload execution in container sandbox",
)
def execute_workload(
    repository_id: uuid.UUID,
    payload: ExecutionRequest,
    db: Session = Depends(get_db),
    worker: DynamicExecutionWorker = Depends(get_execution_worker),
) -> ExecutionReport:
    """Execute an explicitly approved workload profile against a registered target repository."""
    # 1. Verify target repository exists in catalog
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    # 2. Reject unknown profiles early before snapshot acquisition
    if payload.profile_id not in WORKLOAD_PROFILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workload profile '{payload.profile_id}' is not permitted. Arbitrary commands are strictly forbidden.",
        )

    # 3. Acquire repository snapshot safely
    snapshot_ctx: Optional[SnapshotContext] = None
    try:
        if repo.source_type == "git":
            snapshot_ctx = ingest_git_repository(
                git_url=repo.url,
                timeout_seconds=float(settings.inspection_timeout_seconds),
            )
        else:
            snapshot_ctx = ingest_local_directory(
                local_path=repo.url,
                permitted_roots=settings.permitted_local_roots,
            )

        # 4. Dispatch to dynamic execution worker
        report = worker.execute_workload(
            repository=repo,
            request=payload,
            snapshot_path=snapshot_ctx.root_path,
        )
        return report

    except Exception as ex:
        # If ingestion or security boundary raised an exception
        if "traversal" in str(ex).lower() or "outside permitted" in str(ex).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security violation during snapshot acquisition: {str(ex)}",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution pipeline error: {str(ex)}",
        )
    finally:
        if snapshot_ctx:
            snapshot_ctx.cleanup()


@router.get(
    "/repositories/{repository_id}/execution",
    response_model=ExecutionReport,
    summary="Retrieve latest dynamic execution report for repository",
)
def get_latest_execution(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
    worker: DynamicExecutionWorker = Depends(get_execution_worker),
) -> ExecutionReport:
    """Retrieve the most recent dynamic execution report for a repository target."""
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )

    report = worker.get_latest_report(repository_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No execution report found for repository {repository_id}",
        )

    return report
