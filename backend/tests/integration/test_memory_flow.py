"""Cross-session memory flow integration tests."""

import json
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.core.memory.bm25 import BM25Index
from app.core.memory.service import MemoryService
from app.core.memory.store import MemoryVectorIndex
from app.core.storage.inmemory import InMemoryVectorStore
from app.deps import _globals, init_deps
from app.graph_seed import ensure_default_graph
from app.main import app
from tests.unit.test_retrieval import FakeEmbedder


class MemoryAwareLLM:
    """Fake LLM that makes memory influence visible in the final answer."""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        _ = system
        if "Decompose the query" in prompt:
            return json.dumps({"steps": [{"type": "generate", "input": "recommend stack"}]})
        if "Is this answer good" in prompt:
            return '{"quality": "good", "reason": "ok"}'
        if "Synthesize a final answer" in prompt:
            return "Use Python for the stack." if "I prefer Python" in prompt else "No memory used."
        return "noted"

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        text = await self.complete(prompt, system=system)
        for char in text:
            yield char


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
    _globals["llm"] = MemoryAwareLLM()
    _globals["retrieval"]._embedder = embedder  # type: ignore[attr-defined]
    _globals["memory"] = MemoryService(
        db_session.get_session_factory(),
        MemoryVectorIndex(embedder, InMemoryVectorStore()),
        BM25Index(),
    )
    async with db_session.get_session_factory()() as session:
        await ensure_default_graph(session)
    return TestClient(app)


async def test_chat_persists_user_memory_and_recalls_it_in_later_complex_task() -> None:
    """A later chat should recall earlier user memory and use it in generation."""

    client = await _setup()

    first = client.post("/chat", json={"query": "hi I prefer Python"})
    assert first.status_code == 200

    second = client.post("/chat", json={"query": "compare stack and give advice"})
    assert second.status_code == 200
    assert "Use Python for the stack." in second.text

    run = client.get(f"/runs/{_trace_id(second.text)}").json()
    recall_io = next(entry for entry in run["node_io"] if entry["node_id"] == "memory_recall")
    assert recall_io["output"]["memory_hits"][0]["content"] == "hi I prefer Python"


def _trace_id(sse_body: str) -> str:
    line = next(line for line in sse_body.splitlines() if line.startswith("data: {"))
    return str(json.loads(line.removeprefix("data: "))["trace_id"])
