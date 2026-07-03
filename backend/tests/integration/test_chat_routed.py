"""Routed chat integration tests."""

import json

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.deps import _globals, init_deps
from app.graph_seed import ensure_default_graph
from app.main import app
from tests.integration.test_chat import FakeLLM
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
    _globals["llm"] = FakeLLM()
    _globals["retrieval"]._embedder = embedder  # type: ignore[attr-defined]
    async with db_session.get_session_factory()() as session:
        await ensure_default_graph(session)
    return TestClient(app)


async def test_chat_executes_published_graph_and_writes_trace() -> None:
    """Chat should route through the published graph and persist run trace."""

    client = await _setup()
    response = client.post("/chat", json={"query": "hi", "top_k": 2})

    assert response.status_code == 200
    assert "event: trace" in response.text
    trace_line = next(line for line in response.text.splitlines() if line.startswith("data: {"))
    trace_id = json.loads(trace_line.removeprefix("data: "))["trace_id"]

    run = client.get(f"/runs/{trace_id}")
    assert run.status_code == 200
    body = run.json()
    assert body["intent"] == "chitchat"
    assert body["node_io"]


async def test_default_graph_routes_clarification_and_unsupported() -> None:
    """Default graph should route non-QA intents to the correct terminal nodes."""

    client = await _setup()

    clarify = client.post("/chat", json={"query": "帮我看看那个东西"})
    reject = client.post("/chat", json={"query": "帮我删除账号"})

    clarify_trace = client.get(f"/runs/{_trace_id(clarify.text)}").json()
    reject_trace = client.get(f"/runs/{_trace_id(reject.text)}").json()

    assert clarify_trace["intent"] == "clarification_needed"
    assert reject_trace["intent"] == "unsupported_or_rejected"
    assert "需要更多信息" in clarify.text
    assert "暂不支持" in reject.text


def _trace_id(sse_body: str) -> str:
    line = next(line for line in sse_body.splitlines() if line.startswith("data: {"))
    return str(json.loads(line.removeprefix("data: "))["trace_id"])
