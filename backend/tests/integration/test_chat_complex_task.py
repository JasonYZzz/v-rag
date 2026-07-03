"""Complex-task routed chat integration tests."""

import json
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.db import session as db_session
from app.core.db.models import Base
from app.deps import _globals, init_deps
from app.graph_seed import ensure_default_graph
from app.main import app
from tests.unit.test_retrieval import FakeEmbedder


class PlanningLLM:
    """Fake LLM that supports planner, executor, synthesizer, and reflect prompts."""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        _ = system
        if "Decompose the query" in prompt:
            return json.dumps(
                {
                    "steps": [
                        {"type": "tool", "input": {"tool": "search_web", "args": {"q": "A"}}},
                        {"type": "generate", "input": "compare A B C"},
                    ]
                }
            )
        if "Is this answer good" in prompt:
            return '{"quality": "good", "reason": "complete"}'
        if "Synthesize a final answer" in prompt:
            return "A is the best fit."
        return "step draft"

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
    _globals["llm"] = PlanningLLM()
    _globals["retrieval"]._embedder = embedder  # type: ignore[attr-defined]
    async with db_session.get_session_factory()() as session:
        await ensure_default_graph(session)
    return TestClient(app)


async def test_complex_task_routes_through_planning_branch_and_persists_trace() -> None:
    """Complex task chats should execute planner -> executor loop -> synthesizer -> reflect."""

    client = await _setup()

    response = client.post("/chat", json={"query": "对比 A B C 三款产品并给建议"})

    assert response.status_code == 200
    assert "A is the best fit." in response.text
    run = client.get(f"/runs/{_trace_id(response.text)}")
    assert run.status_code == 200
    body = run.json()
    assert body["intent"] == "complex_task"
    assert body["route_trace"]["final_intent"] == "complex_task"
    node_ids = [entry["node_id"] for entry in body["node_io"]]
    assert node_ids == [
        "classifier",
        "memory_recall",
        "planner",
        "executor",
        "executor",
        "synthesizer",
        "reflect",
        "memory_write",
    ]
    planner_io = next(entry for entry in body["node_io"] if entry["node_id"] == "planner")
    executor_io = [entry for entry in body["node_io"] if entry["node_id"] == "executor"]
    assert planner_io["output"]["plan"][0]["type"] == "tool"
    assert executor_io[0]["output"]["step_results"][0]["result"]["tool"] == "search_web"


def _trace_id(sse_body: str) -> str:
    line = next(line for line in sse_body.splitlines() if line.startswith("data: {"))
    return str(json.loads(line.removeprefix("data: "))["trace_id"])
