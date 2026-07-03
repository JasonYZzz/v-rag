"""Graphs API integration tests."""

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.deps import _globals, init_deps
from app.main import app
from tests.integration.test_chat import FakeLLM
from tests.unit.test_retrieval import FakeEmbedder

RAW_GRAPH = {
    "entry": "classifier",
    "nodes": [
        {"id": "classifier", "type": "classifier"},
        {"id": "clarify", "type": "clarification"},
    ],
    "edges": [{"from": "classifier", "to": "clarify"}],
    "exits": ["clarify"],
}


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
    _globals["llm"] = FakeLLM()
    _globals["retrieval"]._embedder = embedder  # type: ignore[attr-defined]
    return TestClient(app)


async def test_graphs_create_draft_test_run_publish_and_rollback() -> None:
    """Graphs API should expose the version lifecycle."""

    client = await _setup()

    created = client.post("/graphs", json={"name": "Test", "graph": RAW_GRAPH})
    assert created.status_code == 200
    config_id = created.json()["id"]
    version = created.json()["version"]

    drafted = client.put(f"/graphs/{config_id}/draft", json={"graph": RAW_GRAPH})
    assert drafted.status_code == 200
    draft_version = drafted.json()["version"]

    test_run = client.post(
        f"/graphs/{config_id}/test-run",
        json={"version": draft_version, "query": "帮我看看"},
    )
    assert test_run.status_code == 200
    assert test_run.json()["state"]["generation"]

    published = client.post(f"/graphs/{config_id}/publish", json={"version": version})
    assert published.status_code == 200
    rolled = client.post(f"/graphs/{config_id}/rollback", json={"version": draft_version})
    assert rolled.status_code == 200

    listed = client.get("/graphs")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == config_id


async def test_graphs_registry_exposes_node_whitelist() -> None:
    """Registry endpoint should expose backend whitelisted node types."""

    client = await _setup()

    response = client.get("/graphs/registry")

    assert response.status_code == 200
    body = response.json()
    types = {item["type"] for item in body}
    assert {
        "classifier",
        "retrieve",
        "generate",
        "clarification",
        "unsupported",
        "memory_recall",
        "memory_write",
        "reflect",
    }.issubset(types)
    classifier = next(item for item in body if item["type"] == "classifier")
    assert classifier["description"]
    assert "config_schema" in classifier
