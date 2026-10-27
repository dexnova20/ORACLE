"""Repository management API endpoints."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from oracle.db.session import get_db
from oracle.diagnostics.service import diagnostic_orchestrator
from oracle.models.repository import Repository, RepositoryStatus, utc_now
from oracle.schemas.repository import RepositoryCreate, RepositoryResponse

router = APIRouter()


@router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register diagnostic target repository",
    description="Registers repository metadata for future inspection. Does not clone or execute code.",
)
def register_repository(
    payload: RepositoryCreate,
    db: Session = Depends(get_db),
) -> RepositoryResponse:
    """Register a new repository diagnostic target."""
    now = utc_now()
    repo = Repository(
        id=uuid.uuid4(),
        name=payload.name,
        url=payload.url,
        source_type=payload.source_type.value,
        status=RepositoryStatus.REGISTERED.value,
        created_at=now,
        updated_at=now,
    )
    # Always register in orchestrator memory store for immediate pipeline availability
    diagnostic_orchestrator.register_repo(repo)

    # Persist to database if operational
    try:
        db.add(repo)
        db.commit()
        db.refresh(repo)
    except OperationalError:
        db.rollback()
    except Exception:
        db.rollback()
        raise

    return RepositoryResponse.model_validate(repo)


@router.get(
    "",
    response_model=List[RepositoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List registered repositories",
    description="Returns all registered repository diagnostic targets.",
)
def list_repositories(
    db: Session = Depends(get_db),
) -> List[RepositoryResponse]:
    """Retrieve all registered repositories ordered by registration date."""
    try:
        stmt = select(Repository).order_by(Repository.created_at.desc())
        db_repos = list(db.scalars(stmt).all())
        return [RepositoryResponse.model_validate(r) for r in db_repos]
    except OperationalError:
        mem_repos = diagnostic_orchestrator.list_repos()
        return [RepositoryResponse.model_validate(r) for r in mem_repos]


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get repository details",
    description="Retrieve metadata for a specific registered repository target.",
)
def get_repository(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> RepositoryResponse:
    """Retrieve a single repository target by UUID."""
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
    return RepositoryResponse.model_validate(repo)


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete repository registration",
    description="Removes only the registered metadata record. Does not delete remote or local code.",
)
def delete_repository(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    """Remove repository metadata from ORACLE catalog."""
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

    diagnostic_orchestrator.delete_repo(repository_id)
    try:
        db.delete(repo)
        db.commit()
    except Exception:
        db.rollback()

    return None
