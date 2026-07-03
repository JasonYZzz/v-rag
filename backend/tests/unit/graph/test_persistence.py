"""Graph persistence service tests."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db.models import Base
from app.core.graph.config import GraphConfig
from app.core.graph.persistence import (
    create_graph,
    get_published,
    get_version,
    list_graphs,
    publish_version,
    rollback_to,
    save_draft_version,
)

RAW_GRAPH = {
    "entry": "classifier",
    "nodes": [{"id": "classifier", "type": "classifier"}],
    "edges": [],
    "exits": ["classifier"],
}


async def _session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory()


async def test_graph_version_publish_and_rollback_flow() -> None:
    """Persistence service should manage drafts, publish, and rollback."""

    async with await _session() as session:
        config, version = await create_graph(session, "Default", GraphConfig.model_validate(RAW_GRAPH))
        draft = await save_draft_version(session, config.id, GraphConfig.model_validate(RAW_GRAPH))

        await publish_version(session, config.id, version.version)
        await rollback_to(session, config.id, draft.version)

        graphs = await list_graphs(session)
        published = await get_published(session, config.id)
        loaded_draft = await get_version(session, config.id, draft.version)

        assert graphs[0].id == config.id
        assert published is not None
        assert published.version == 2
        assert loaded_draft.status == "published"
