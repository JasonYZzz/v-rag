"""Document list and delete integration tests."""

import io

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.deps import _globals, init_deps
from app.main import app
from tests.unit.test_retrieval import FakeEmbedder


async def _reset_deps() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", vector_store="inmemory")
    init_deps(settings)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_session._engine = engine
    db_session._session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedder = FakeEmbedder()
    _globals["embedder"] = embedder
    _globals["retrieval"]._embedder = embedder  # type: ignore[attr-defined]


async def test_list_and_delete_documents_updates_metadata_and_vector_store() -> None:
    """Documents should list after upload and disappear after delete."""

    await _reset_deps()
    client = TestClient(app)
    upload = client.post(
        "/documents",
        files={"file": ("note.txt", io.BytesIO(b"abc abc"), "text/plain")},
    )
    assert upload.status_code == 200
    document_id = upload.json()["document_id"]

    listed = client.get("/documents")
    assert listed.status_code == 200
    docs = listed.json()
    assert len(docs) == 1
    assert docs[0]["id"] == document_id
    assert docs[0]["filename"] == "note.txt"
    assert docs[0]["chunks"] == 1

    delete = client.delete(f"/documents/{document_id}")
    assert delete.status_code == 200
    assert delete.json() == {"deleted": document_id}

    listed_after_delete = client.get("/documents")
    assert listed_after_delete.status_code == 200
    assert listed_after_delete.json() == []

    hits = await _globals["store"].search([1.0, 1.0, 1.0, 0.0], top_k=5)  # type: ignore[attr-defined]
    assert hits == []
