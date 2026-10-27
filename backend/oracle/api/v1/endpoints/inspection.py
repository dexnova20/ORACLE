"""API v1 endpoints for repository snapshot ingestion and static inspection."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from oracle.db.session import get_db
from oracle.diagnostics.service import diagnostic_orchestrator
from oracle.inspection.service import inspection_service
from oracle.models.repository import Repository
from oracle.schemas.inspection import InspectionOptions, InspectionReport

router = APIRouter()


@router.post(
    "/{repository_id}/inspect",
    response_model=InspectionReport,
    status_code=status.HTTP_200_OK,
    summary="Trigger static repository inspection",
    description="Acquires a safe snapshot, detects ecosystems, and constructs a static dependency graph without code execution.",
)
def inspect_repository(
    repository_id: uuid.UUID,
    options: Optional[InspectionOptions] = None,
    db: Session = Depends(get_db),
) -> InspectionReport:
    """Execute bounded static inspection on a registered repository target."""
    repo = None
    try:
        repo = db.get(Repository, repository_id)
    except Exception:
        pass

    if not repo:
        repo = diagnostic_orchestrator.get_repo(repository_id)

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found.",
        )

    report = inspection_service.inspect_repository(repo, options=options)

    if report.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository inspection failed: {report.error_message}",
        )

    return report


@router.get(
    "/{repository_id}/inspection",
    response_model=InspectionReport,
    status_code=status.HTTP_200_OK,
    summary="Retrieve latest repository inspection report",
    description="Returns the most recent static inspection report for a registered repository.",
)
def get_latest_inspection(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> InspectionReport:
    """Retrieve the latest inspection report for a repository target."""
    repo = None
    try:
        repo = db.get(Repository, repository_id)
    except Exception:
        pass

    if not repo:
        repo = diagnostic_orchestrator.get_repo(repository_id)

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found.",
        )

    report = inspection_service.get_latest_report(repository_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inspection report found for repository '{repository_id}'. Trigger inspection via POST first.",
        )

    return report
