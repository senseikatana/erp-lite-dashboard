"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine

logger = logging.getLogger("erp_lite")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare the database before serving traffic.

    Schema creation lives here rather than in a module-level statement so it
    runs inside the application lifespan and can fail loudly in the logs.
    Use Alembic migrations for anything beyond the initial bootstrap.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Schema ready on %s", "sqlite" if settings.is_sqlite else "postgres")
    yield

    # Disposing returns pooled connections and closes sockets. Against an
    # in-memory SQLite database it would destroy the database itself, so it is
    # skipped there.
    if not settings.is_in_memory:
        engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Multi-company ERP API for sales, purchasing, warehouse and transport "
        "operations, with role-based access and a recorded audit trail."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness and database connectivity probe.

    The database check is not a bare liveness test: a server that cannot reach
    its database cannot serve requests, and a deployment probe that ignores
    that will report healthy while the app is useless.
    """
    database_ok = True
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - probe must never raise
        logger.exception("Health check could not reach the database")
        database_ok = False

    return {
        "status": "ok" if database_ok else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "ok" if database_ok else "unreachable",
    }


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Map domain validation errors to 422 rather than 500.

    Services raise ``ValueError`` subclasses for business-rule violations that
    are the caller's fault, so they must not surface as server errors.
    """
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )