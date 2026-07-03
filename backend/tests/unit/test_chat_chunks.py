"""Chat SSE retrieved chunk event tests."""

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.core.retrieval.engine import RetrievedChunk
from app.deps import _globals, init_deps
from app.main import app


class FakeRetrieval:
    """Retrieval engine returning one fixed hit."""

    async def search(
        self,
        query: str,
        top_k: int = 4,
        filter: dict[str, object] | None = None,
        text_lookup: dict[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        _ = (query, top_k, filter, text_lookup)
        return [
            RetrievedChunk(
                chunk_id="chunk-1",
                text="retrieved text",
                score=0.91,
                metadata={"page": 2, "doc": "doc-1"},
            )
        ]


class FakeLLM:
    """LLM returning one token."""

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        _ = (prompt, system)
        yield "Hi"

    async def complete(self, prompt: str, *, system: str = "") -> str:
        return "".join([token async for token in self.stream(prompt, system=system)])


class FakeEmbedder:
    @property
    def dim(self) -> int:
        return 1

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]


def test_chat_emits_retrieved_event_before_tokens() -> None:
    """The first SSE frame should be the retrieved chunks event."""

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
    _globals["retrieval"] = FakeRetrieval()
    _globals["llm"] = FakeLLM()
    _globals["embedder"] = FakeEmbedder()
    client = TestClient(app)

    response = client.post("/chat", json={"query": "what is alpha", "top_k": 1})

    assert response.status_code == 200
    frames = response.text.strip().split("\n\n")
    assert frames[0].startswith("event: retrieved\n")
    assert '"chunk_id": "chunk-1"' in frames[0]
    assert '"text": "retrieved text"' in frames[0]
    assert '"score": 0.91' in frames[0]
    assert frames[2] == "event: generation\ndata: Hi"
    assert frames[3] == "data: H"
    assert frames[4] == "data: i"
    assert frames[-1] == "data: [DONE]"
