"""Chat endpoint integration tests."""

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.deps import _globals, init_deps
from app.main import app
from tests.unit.test_retrieval import FakeEmbedder


class FakeLLM:
    """Fake streaming LLM."""

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        """Yield a deterministic response."""

        _ = (prompt, system)
        for token in ["你", "好"]:
            yield token

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Return the deterministic response."""

        return "".join([token async for token in self.stream(prompt, system=system)])


def test_chat_streams_sse() -> None:
    """Chat should stream SSE tokens and a done marker."""

    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", vector_store="inmemory")
    init_deps(settings)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    import anyio

    async def create_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    anyio.run(create_tables)
    db_session._engine = engine
    db_session._session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedder = FakeEmbedder()
    _globals["llm"] = FakeLLM()
    _globals["embedder"] = embedder
    _globals["retrieval"]._embedder = embedder  # type: ignore[attr-defined]

    client = TestClient(app)
    response = client.post("/chat", json={"query": "hi", "top_k": 2})

    assert response.status_code == 200
    body = response.text
    assert "data: 你" in body
    assert "data: 好" in body
    assert "[DONE]" in body
