"""API v1 endpoints for ORACLE unified diagnostic engine and evidence pipeline."""

import json
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from oracle.db.session import get_db
from oracle.diagnostics.service import diagnostic_orchestrator
from oracle.execution.policy import WORKLOAD_PROFILES
from oracle.models.diagnostic_run import DiagnosticRunRecord
from oracle.models.repository import Repository
from oracle.schemas.diagnostics import (
    DiagnosticDecisionsResponse,
    DiagnosticProbesResponse,
    DiagnosticReport,
    DiagnosticRunRequest,
)

router = APIRouter()


@router.post(
    "/repositories/{repository_id}/diagnose",
    response_model=DiagnosticReport,
    status_code=status.HTTP_200_OK,
    summary="Trigger end-to-end diagnostic workflow",
    description=(
        "Executes the full ORACLE diagnostic pipeline: safe ingestion, static inspection, "
        "system mapping, evidence collection, fault hypothesis generation, safe verification, "
        "and report assembly."
    ),
)
def run_diagnosis(
    repository_id: uuid.UUID,
    payload: Optional[DiagnosticRunRequest] = None,
    db: Session = Depends(get_db),
) -> DiagnosticReport:
    """Trigger a full diagnostic evaluation on a registered target repository."""
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

    if payload and payload.workload_profile and payload.workload_profile not in WORKLOAD_PROFILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workload profile '{payload.workload_profile}' is not in the approved allowlist. Arbitrary execution is prohibited.",
        )

    try:
        report = diagnostic_orchestrator.execute_diagnosis(
            repository=repo,
            request=payload,
            db=db,
        )
        return report
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )


@router.get(
    "/repositories/{repository_id}/diagnostics/latest",
    response_model=DiagnosticReport,
    status_code=status.HTTP_200_OK,
    summary="Get latest diagnostic report for repository",
    description="Returns the most recent end-to-end diagnostic report for a specific repository target.",
)
def get_latest_diagnostic_report(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DiagnosticReport:
    """Retrieve the latest diagnostic report for a repository target."""
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

    report = diagnostic_orchestrator.get_latest_report(repository_id)
    if report:
        return report

    # Fallback to database persistence if available
    try:
        stmt = (
            select(DiagnosticRunRecord)
            .filter(DiagnosticRunRecord.repository_id == repository_id)
            .order_by(DiagnosticRunRecord.created_at.desc())
            .limit(1)
        )
        record = db.scalars(stmt).first()
        if record and record.report_json:
            try:
                return DiagnosticReport.model_validate_json(record.report_json)
            except Exception:
                pass
    except Exception:
        pass

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No diagnostic report found for repository '{repository_id}'. Initiate diagnosis first.",
    )


@router.get(
    "/diagnostics/runs",
    response_model=List[DiagnosticReport],
    status_code=status.HTTP_200_OK,
    summary="List all diagnostic runs",
    description="Retrieves a list of recent diagnostic runs across all registered targets.",
)
def list_diagnostic_runs(
    db: Session = Depends(get_db),
) -> List[DiagnosticReport]:
    """Retrieve recent diagnostic reports ordered by start timestamp, merging in-memory and database records."""
    memory_runs = diagnostic_orchestrator.list_runs()
    runs_by_id = {run.run_id: run for run in memory_runs}

    # Query persistent database records if available
    try:
        db_records = (
            db.query(DiagnosticRunRecord)
            .order_by(DiagnosticRunRecord.created_at.desc())
            .limit(100)
            .all()
        )
        for rec in db_records:
            if rec.id not in runs_by_id and rec.report_json:
                try:
                    runs_by_id[rec.id] = DiagnosticReport.model_validate_json(rec.report_json)
                except Exception:
                    pass
    except Exception:
        pass

    return sorted(runs_by_id.values(), key=lambda r: r.started_at, reverse=True)


@router.get(
    "/diagnostics/{run_id}",
    response_model=DiagnosticReport,
    status_code=status.HTTP_200_OK,
    summary="Get diagnostic run by UUID",
    description="Retrieve a specific diagnostic report by its run UUID.",
)
def get_diagnostic_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DiagnosticReport:
    """Retrieve a specific diagnostic run by its unique identifier."""
    report = diagnostic_orchestrator.get_run(run_id)
    if report:
        return report

    # Query from database persistence if not in memory
    record = db.get(DiagnosticRunRecord, run_id)
    if record and record.report_json:
        try:
            return DiagnosticReport.model_validate_json(record.report_json)
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Diagnostic run '{run_id}' not found.",
    )


@router.get(
    "/diagnostics/{run_id}/probes",
    response_model=DiagnosticProbesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get candidate and executed probes for a diagnostic run",
    description="Retrieve candidate and executed diagnostic probes, outcomes, and stopping conditions.",
)
def get_diagnostic_probes(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DiagnosticProbesResponse:
    """Retrieve candidate and executed probes for a specific diagnostic run."""
    report = get_diagnostic_run(run_id=run_id, db=db)
    return DiagnosticProbesResponse(
        run_id=report.run_id,
        candidate_probes=report.candidate_probes,
        executed_probes=report.executed_probes,
        stopping_reason=report.stopping_reason,
    )


@router.get(
    "/diagnostics/{run_id}/decisions",
    response_model=DiagnosticDecisionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get adaptive investigation decision history",
    description="Retrieve step-by-step planner decision records and rationale for an adaptive diagnostic run.",
)
def get_diagnostic_decisions(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DiagnosticDecisionsResponse:
    """Retrieve adaptive investigation decisions for a specific diagnostic run."""
    report = get_diagnostic_run(run_id=run_id, db=db)
    return DiagnosticDecisionsResponse(
        run_id=report.run_id,
        decisions=report.investigation_history,
        stopping_reason=report.stopping_reason,
    )

