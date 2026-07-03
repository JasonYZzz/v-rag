"""Memories API integration tests."""

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.core.memory.bm25 import BM25Index
from app.core.memory.schemas import MemoryIn
from app.core.memory.service import MemoryService
from app.core.memory.store import MemoryVectorIndex
from app.core.storage.inmemory import InMemoryVectorStore
from app.deps import _globals, init_deps
from app.main import app
from tests.unit.test_retrieval import FakeEmbedder


async def _setup() -> TestClient:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", vector_store="inmemory")
    init_deps(settings)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_session._engine = engine
    db_session._session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedder = FakeEmbedder()
    _globals["embedder"] = embedder
    _globals["memory"] = MemoryService(
        db_session.get_session_factory(),
        MemoryVectorIndex(embedder, InMemoryVectorStore()),
        BM25Index(),
    )
    await _globals["memory"].remember(MemoryIn(content="I prefer Python", user_id="u1"))  # type: ignore[attr-defined]
    return TestClient(app)


async def test_memories_api_lists_updates_feedback_and_forgets() -> None:
    """Memories API should support viewer backend lifecycle operations."""

    client = await _setup()

    listed = client.get("/memories", params={"user_id": "u1"})
    assert listed.status_code == 200
    memory = listed.json()[0]
    assert memory["content"] == "I prefer Python"

    patched = client.patch(f"/memories/{memory['id']}", json={"importance": 0.88, "status": "active"})
    assert patched.status_code == 200
    assert patched.json()["importance"] == 0.88

    feedback = client.post(f"/memories/{memory['id']}/feedback", json={"feedback": "correct"})
    assert feedback.status_code == 200
    assert feedback.json() == {"ok": True}

    forgotten = client.request("DELETE", "/memories", json={"ids": [memory["id"]]})
    assert forgotten.status_code == 200
    assert forgotten.json() == {"deleted": 1}

    after = client.get("/memories", params={"user_id": "u1", "status": "active"})
    assert after.status_code == 200
    assert after.json() == []
