"""Persistence helpers for versioned graph configs."""

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.models import AgentGraphConfig, AgentGraphVersion, PublishHistory
from app.core.graph.config import GraphConfig


async def create_graph(
    session: AsyncSession,
    name: str,
    graph: GraphConfig,
    workspace_id: str = "default",
) -> tuple[AgentGraphConfig, AgentGraphVersion]:
    """Create a graph config with version 1 as draft."""

    config = AgentGraphConfig(name=name, workspace_id=workspace_id)
    session.add(config)
    await session.flush()
    version = AgentGraphVersion(
        config_id=config.id,
        version=1,
        graph=graph.model_dump(mode="json", by_alias=True),
        status="draft",
    )
    session.add(version)
    await session.commit()
    await session.refresh(config)
    await session.refresh(version)
    return config, version


async def save_draft_version(
    session: AsyncSession,
    config_id: str,
    graph: GraphConfig,
) -> AgentGraphVersion:
    """Save a new draft version."""

    next_version = await _next_version(session, config_id)
    version = AgentGraphVersion(
        config_id=config_id,
        version=next_version,
        graph=graph.model_dump(mode="json", by_alias=True),
        status="draft",
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


async def list_graphs(session: AsyncSession) -> list[AgentGraphConfig]:
    """List graph configs."""

    result = await session.execute(select(AgentGraphConfig).order_by(AgentGraphConfig.created_at))
    return list(result.scalars().all())


async def list_versions(session: AsyncSession, config_id: str) -> list[AgentGraphVersion]:
    """List versions for a config."""

    result = await session.execute(
        select(AgentGraphVersion)
        .where(AgentGraphVersion.config_id == config_id)
        .order_by(AgentGraphVersion.version)
    )
    return list(result.scalars().all())


async def get_version(
    session: AsyncSession, config_id: str, version: int
) -> AgentGraphVersion:
    """Load a specific graph version."""

    result = await session.execute(
        select(AgentGraphVersion).where(
            AgentGraphVersion.config_id == config_id,
            AgentGraphVersion.version == version,
        )
    )
    return result.scalar_one()


async def publish_version(
    session: AsyncSession, config_id: str, version: int
) -> AgentGraphVersion:
    """Publish a draft version and archive older published versions."""

    selected = await get_version(session, config_id, version)
    await session.execute(
        update(AgentGraphVersion)
        .where(
            AgentGraphVersion.config_id == config_id,
            AgentGraphVersion.status == "published",
        )
        .values(status="archived")
    )
    selected.status = "published"
    config = await session.get(AgentGraphConfig, config_id)
    if config is not None:
        config.current_published_version = version
    session.add(PublishHistory(config_id=config_id, version=version, action="publish"))
    await session.commit()
    await session.refresh(selected)
    return selected


async def rollback_to(session: AsyncSession, config_id: str, version: int) -> AgentGraphVersion:
    """Rollback by making a historical version the current published version."""

    selected = await get_version(session, config_id, version)
    await session.execute(
        update(AgentGraphVersion)
        .where(
            AgentGraphVersion.config_id == config_id,
            AgentGraphVersion.status == "published",
        )
        .values(status="archived")
    )
    selected.status = "published"
    config = await session.get(AgentGraphConfig, config_id)
    if config is not None:
        config.current_published_version = version
    session.add(PublishHistory(config_id=config_id, version=version, action="rollback"))
    await session.commit()
    await session.refresh(selected)
    return selected


async def get_published(
    session: AsyncSession, config_id: str | None = None
) -> AgentGraphVersion | None:
    """Return the currently published version for a config or first available config."""

    stmt = select(AgentGraphConfig)
    if config_id is not None:
        stmt = stmt.where(AgentGraphConfig.id == config_id)
    stmt = stmt.where(AgentGraphConfig.current_published_version.is_not(None)).order_by(
        AgentGraphConfig.created_at
    )
    config = (await session.execute(stmt)).scalars().first()
    if config is None or config.current_published_version is None:
        return None
    return await get_version(session, config.id, config.current_published_version)


async def delete_graph(session: AsyncSession, config_id: str) -> None:
    """Delete a graph config and cascaded versions/history."""

    await session.execute(delete(AgentGraphConfig).where(AgentGraphConfig.id == config_id))
    await session.commit()


async def _next_version(session: AsyncSession, config_id: str) -> int:
    result = await session.execute(
        select(func.max(AgentGraphVersion.version)).where(AgentGraphVersion.config_id == config_id)
    )
    return int(result.scalar() or 0) + 1
