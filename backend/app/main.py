from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.chat import router as chat_router
from app.api.v1.history import router as history_router
from app.api.v1.recommend import router as recommend_router
from app.api.v1.resume import router as resume_router
from app.api.v1.roadmap import router as roadmap_router
from app.core.config import settings


# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================================
# Application lifespan
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.

    ML artifacts are loaded during application startup so that
    problems with the recommendation engine are detected before
    the API begins serving requests.
    """

    logger.info(
        "Starting Career Recommendation API..."
    )

    try:
        from app.ml import inference

        logger.info(
            "ML inference engine loaded successfully."
        )

        logger.info(
            "Loaded %d occupation profiles.",
            len(inference.occupation_order),
        )

    except Exception as exc:
        logger.exception(
            "Failed to load ML inference engine: %s",
            exc,
        )
        raise

    logger.info(
        "Environment: %s",
        settings.ENVIRONMENT,
    )

    logger.info(
        "API startup completed."
    )

    yield

    logger.info(
        "Career Recommendation API shutting down."
    )


# ============================================================================
# FastAPI application
# ============================================================================

app = FastAPI(
    title="AI Career Recommendation System",
    description=(
        "AI-based career recommendation and guidance API "
        "using O*NET occupational data, machine learning, "
        "and LLM services."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ============================================================================
# CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Global exception handler
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    """
    Handle unexpected application errors.

    Detailed error information is logged on the server but is not
    exposed to the API client.
    """

    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error.",
        },
    )


# ============================================================================
# Health
# ============================================================================

@app.get(
    "/health",
    tags=["Health"],
)
async def health_check():
    """
    Basic API health check.
    """

    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


# ============================================================================
# Root
# ============================================================================

@app.get(
    "/",
    tags=["Health"],
)
async def root():
    """
    API root endpoint.
    """

    return {
        "name": "AI Career Recommendation System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


# ============================================================================
# API v1 routers
# ============================================================================

app.include_router(
    recommend_router,
    prefix="/api/v1",
)

app.include_router(
    resume_router,
    prefix="/api/v1",
)

app.include_router(
    roadmap_router,
    prefix="/api/v1",
)

app.include_router(
    chat_router,
    prefix="/api/v1",
)


# ============================================================================
# History router
# ============================================================================

app.include_router(
    history_router,
)