"""
Database connection and session management
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
import structlog

from config import settings

logger = structlog.get_logger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    poolclass=NullPool,  # Disable pooling for simpler management
    echo=False,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that yields database sessions.
    Use with FastAPI's Depends().
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize database - create all tables and load settings.
    Called on application startup.
    """
    from .models import Base
    from . import crud

    logger.info("Initializing database...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize default settings and load into runtime config
    async with AsyncSessionLocal() as session:
        await crud.init_default_settings(session)
        await session.commit()

        # Load settings from DB into runtime config
        settings_list = await crud.get_all_settings(session)
        for setting in settings_list:
            if setting.value:
                _update_runtime_setting(setting.key, setting.value)

    logger.info("Database initialized successfully")


def _update_runtime_setting(key: str, value: str) -> None:
    """Update runtime settings singleton"""
    if key == "DEEPGRAM_API_KEY":
        settings.DEEPGRAM_API_KEY = value
    elif key == "MURF_API_KEY":
        settings.MURF_API_KEY = value
    elif key == "OPENAI_API_KEY":
        settings.OPENAI_API_KEY = value


async def close_db() -> None:
    """
    Close database connections.
    Called on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")
