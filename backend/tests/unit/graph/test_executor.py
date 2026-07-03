"""Executor node tests."""

from typing import Any, cast

from app.core.graph.nodes.executor import execute_step, should_continue
from app.core.graph.state import VragState
from app.core.tools.registry import ToolDefinition, ToolRegistry


class Hit:
    """Fake retrieval hit."""

    def __init__(self) -> None:
        self.chunk_id = "c1"
        self.text = "context"
        self.score = 0.9
        self.metadata = {"page": 1}


class FakeRetrieval:
    """Fake retrieval service."""

    async def search(self, query: str, top_k: int = 4) -> list[Hit]:
        assert query == "find context"
        assert top_k == 4
        return [Hit()]


class FakeLLM:
    """Fake generation service."""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        _ = system
        return f"generated: {prompt}"


async def fake_tool(args: dict[str, Any], services: Any) -> dict[str, Any]:
    """Fake registered tool."""

    _ = services
    return {"called_with": args}


class Services:
    """Fake graph services."""

    def __init__(self) -> None:
        self.retrieval = FakeRetrieval()
        self.llm = FakeLLM()
        self.tools = ToolRegistry()
        self.tools.register(ToolDefinition("search_web", "Search", None, fake_tool))


async def test_executor_runs_one_step_at_a_time_and_advances_cursor() -> None:
    """Executor should run the current step and append normalized results."""

    state = VragState(
        query="q",
        messages=[],
        current_step=0,
        step_results=[],
        plan=[
            {"type": "retrieve", "input": "find context"},
            {"type": "tool", "input": {"tool": "search_web", "args": {"q": "A"}}},
            {"type": "generate", "input": "draft answer"},
        ],
    )
    services = Services()

    first = await execute_step(state, {}, services)
    state = cast(VragState, {**state, **first})
    second = await execute_step(state, {}, services)
    state = cast(VragState, {**state, **second})
    third = await execute_step(state, {}, services)
    state = cast(VragState, {**state, **third})

    assert state["current_step"] == 3
    assert len(state["step_results"]) == 3
    assert state["step_results"][0]["docs"][0]["text"] == "context"
    assert state["step_results"][1]["result"] == {"called_with": {"q": "A"}}
    assert state["step_results"][2]["text"] == "generated: draft answer"
    assert should_continue(state) == "synthesizer"


async def test_executor_records_unknown_step_type_as_error() -> None:
    """Unknown step types should be visible in trace without crashing."""

    state = VragState(
        query="q",
        messages=[],
        current_step=0,
        step_results=[],
        plan=[{"type": "unknown", "input": "x"}],
    )

    result = await execute_step(state, {}, Services())

    assert result["current_step"] == 1
    assert result["step_results"][0]["error"] == "unknown step type: unknown"
    assert should_continue(cast(VragState, {"query": "q", "messages": [], **result})) == "synthesizer"


def test_should_continue_returns_executor_until_plan_is_complete() -> None:
    """Executor conditional router should loop until all plan steps are done."""

    state = VragState(
        query="q",
        messages=[],
        current_step=1,
        plan=[{"type": "generate", "input": "a"}, {"type": "generate", "input": "b"}],
    )

    assert should_continue(state) == "executor"
