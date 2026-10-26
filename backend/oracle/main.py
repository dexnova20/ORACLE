"""ORACLE application entrypoint."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oracle.api.v1.router import api_router
from oracle.core.config import settings
from oracle.db.session import engine

logger = logging.getLogger("oracle.app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for startup and graceful shutdown procedures."""
    logger.info(
        "ORACLE diagnostic engine starting (app: %s, version: %s, environment: %s)",
        settings.app_name,
        settings.version,
        settings.environment,
    )
    yield
    logger.info("ORACLE graceful shutdown: disposing database connection pool")
    engine.dispose()
    logger.info("ORACLE shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Extensible platform for software system inspection, fault isolation, and diagnosis.",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register versioned API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Root"])
def root_info() -> dict[str, str]:
    """Root metadata endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "docs_url": "/docs",
        "api_v1": settings.api_v1_prefix,
    }
