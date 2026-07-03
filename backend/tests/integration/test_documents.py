"""Document upload integration tests."""

import io

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.deps import _globals, init_deps
from app.main import app
from tests.unit.test_retrieval import FakeEmbedder


async def _create_tables(engine: object) -> None:
    async with engine.begin() as conn:  # type: ignore[attr-defined]
        await conn.run_sync(Base.metadata.create_all)


async def _setup_test_deps() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        vector_store="inmemory",
        embed_provider="openai",
    )
    init_deps(settings)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await _create_tables(engine)
    db_session._engine = engine
    db_session._session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedder = FakeEmbedder()
    _globals["embedder"] = embedder
    _globals["retrieval"]._embedder = embedder  # type: ignore[attr-defined]


async def test_upload_text_document_returns_document_id() -> None:
    """Uploading text should return a document id and chunk count."""

    await _setup_test_deps()
    client = TestClient(app)

    response = client.post(
        "/documents",
        files={"file": ("note.txt", io.BytesIO(b"hello world from vrag"), "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert "document_id" in body
    assert body["chunks"] == "1"
