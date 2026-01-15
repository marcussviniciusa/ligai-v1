"""
FastAPI application factory
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import structlog

from db.database import init_db, close_db

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting LigAI API...")
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down LigAI API...")
    await close_db()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="LigAI API",
        description="API para sistema de chamadas com IA",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from .routes import prompts, calls, dashboard

    app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
    app.include_router(calls.router, prefix="/api/v1/calls", tags=["calls"])
    app.include_router(dashboard.router, tags=["dashboard"])

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "ligai"}

    @app.get("/api/v1/stats")
    async def get_stats():
        """Get system statistics"""
        from db.database import AsyncSessionLocal
        from db import crud

        async with AsyncSessionLocal() as db:
            stats = await crud.get_call_stats(db)
            return stats

    return app
