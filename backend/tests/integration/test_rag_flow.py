"""End-to-end RAG flow tests."""

import io
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.deps import _globals, init_deps
from app.main import app
from tests.unit.test_retrieval import FakeEmbedder


class RecordingLLM:
    """Fake LLM that records prompts for assertions."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        """Record the prompt and stream a deterministic token."""

        _ = system
        self.prompts.append(prompt)
        yield "ok"

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Return a deterministic completion."""

        return "".join([token async for token in self.stream(prompt, system=system)])


async def _create_tables() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_session._engine = engine
    db_session._session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def test_upload_then_chat_injects_retrieved_context() -> None:
    """Upload -> chat should retrieve uploaded text into the LLM prompt."""

    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", vector_store="inmemory")
    init_deps(settings)
    await _create_tables()
    embedder = FakeEmbedder()
    llm = RecordingLLM()
    _globals["embedder"] = embedder
    _globals["llm"] = llm
    _globals["retrieval"]._embedder = embedder  # type: ignore[attr-defined]

    client = TestClient(app)
    upload = client.post(
        "/documents",
        files={
            "file": (
                "note.txt",
                io.BytesIO(b"vrag supports multimodal RAG"),
                "text/plain",
            )
        },
    )
    assert upload.status_code == 200

    chat = client.post("/chat", json={"query": "what does vrag support", "top_k": 1})

    assert chat.status_code == 200
    assert "data: ok" in chat.text
    assert llm.prompts
    assert "vrag supports multimodal RAG" in llm.prompts[0]
