"""Async database session factory and migration entrypoint."""

import asyncio
from pathlib import Path

from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alembic import command

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


async def migrate_schema(database_url: str) -> None:
    """Run Alembic migrations for application startup."""

    await asyncio.to_thread(_upgrade_head, database_url)


def _upgrade_head(database_url: str) -> None:
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
