"""FastAPI main application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import cards_router, levels_router, stats_router

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Repitis API",
    description="Backend API for Spanish reading learning app using FSRS spaced repetition",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cards_router)
app.include_router(stats_router)
app.include_router(levels_router)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    """
    Root endpoint - health check.

    Returns:
        dict: API status and version
    """
    return {
        "status": "healthy",
        "service": "Repitis API",
        "version": "0.1.0",
        "environment": settings.environment,
    }


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        dict: Service health status
    """
    return {"status": "healthy"}


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    """Run on application startup."""
    logger.info(f"Starting Repitis API in {settings.environment} mode")
    logger.info(f"CORS origins: {settings.cors_origins}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Run on application shutdown."""
    logger.info("Shutting down Repitis API")
