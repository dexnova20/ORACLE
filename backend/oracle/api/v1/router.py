"""API version 1 central router registry."""

from fastapi import APIRouter

from oracle.api.v1.endpoints import (
    diagnostics,
    execution,
    health,
    inspection,
    repositories,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="", tags=["System Health"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
api_router.include_router(inspection.router, prefix="/repositories", tags=["Inspection"])
api_router.include_router(execution.router, prefix="", tags=["Dynamic Execution"])
api_router.include_router(diagnostics.router, prefix="", tags=["Diagnostic Engine"])
