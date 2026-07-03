"""Runs API integration tests."""

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base, RunTrace
from app.deps import init_deps
from app.main import app


async def test_get_run_trace_returns_node_level_trace() -> None:
    """GET /runs/{trace_id} should return persisted trace details."""

    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", vector_store="inmemory")
    init_deps(settings)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_session._engine = engine
    db_session._session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with db_session.get_session_factory()() as session:
        session.add(
            RunTrace(
                id="trace-1",
                query="q",
                route_trace={"reason": "rule"},
                node_io=[{"node_id": "classifier"}],
                intent="chitchat",
                budget={},
            )
        )
        await session.commit()

    client = TestClient(app)
    response = client.get("/runs/trace-1")

    assert response.status_code == 200
    assert response.json()["node_io"] == [{"node_id": "classifier"}]
