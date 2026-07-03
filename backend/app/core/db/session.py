"""Async database session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.db.models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> AsyncEngine:
    """Initialize the global async engine."""

    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the global async session factory."""

    if _session_factory is None:
        raise RuntimeError("engine not initialized; call init_engine() first")
    return _session_factory


async def create_schema() -> None:
    """Create metadata tables for P0 local and docker startup."""

    if _engine is None:
        raise RuntimeError("engine not initialized; call init_engine() first")
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
