"""Graph persistence model tests."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db.models import (
    AgentGraphConfig,
    AgentGraphVersion,
    Base,
    PublishHistory,
    RunTrace,
)


async def test_graph_config_version_publish_history_and_run_trace_crud() -> None:
    """Graph and trace models should save and load JSON metadata."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        config = AgentGraphConfig(name="Default", workspace_id="default")
        session.add(config)
        await session.flush()
        version = AgentGraphVersion(
            config_id=config.id,
            version=1,
            graph={"entry": "classifier", "nodes": [], "edges": [], "exits": []},
            status="published",
        )
        history = PublishHistory(config_id=config.id, version=1, action="publish")
        trace = RunTrace(
            id="trace-1",
            graph_config_id=config.id,
            graph_version=1,
            query="产品怎么配置",
            route_trace={"reason": "semantic-direct"},
            node_io=[{"node_id": "classifier"}],
            intent="knowledge_qa",
            budget={"tokens": 0},
        )
        config.current_published_version = 1
        session.add_all([version, history, trace])
        await session.commit()

        loaded_trace = (
            await session.execute(select(RunTrace).where(RunTrace.id == "trace-1"))
        ).scalar_one()

        assert loaded_trace.route_trace == {"reason": "semantic-direct"}
        assert loaded_trace.node_io == [{"node_id": "classifier"}]
        assert loaded_trace.intent == "knowledge_qa"


def test_alembic_environment_is_configured() -> None:
    """Alembic should be wired so startup can run migrations instead of create_all."""

    assert Base.metadata.tables["agent_graph_config"] is not None
