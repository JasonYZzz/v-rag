"""Planner node tests."""

from app.core.graph.nodes.planner import plan
from app.core.graph.state import VragState


class FakeLLM:
    """Fake planner LLM."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.prompt = ""
        self.system = ""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Record the prompt and return a canned planner response."""

        self.prompt = prompt
        self.system = system
        return self.response


class Services:
    """Fake graph services."""

    def __init__(self, response: str) -> None:
        self.llm = FakeLLM(response)


async def test_planner_decomposes_query_into_ordered_steps() -> None:
    """Planner should turn a query into ordered executable steps."""

    services = Services(
        '{"steps": ['
        '{"type": "retrieve", "input": "A"}, '
        '{"type": "tool", "input": {"tool": "search_web", "args": {"q": "B"}}}, '
        '{"type": "generate", "input": "compare"}'
        "]}"
    )

    result = await plan(VragState(query="compare A and B", messages=[]), {}, services)

    assert result == {
        "plan": [
            {"type": "retrieve", "input": "A"},
            {"type": "tool", "input": {"tool": "search_web", "args": {"q": "B"}}},
            {"type": "generate", "input": "compare"},
        ],
        "current_step": 0,
        "step_results": [],
    }
    assert "compare A and B" in services.llm.prompt
    assert services.llm.system == "You are a planning assistant."


async def test_planner_falls_back_to_generate_step_on_invalid_json() -> None:
    """Invalid planner JSON should not break the graph run."""

    result = await plan(VragState(query="compare A and B", messages=[]), {}, Services("not json"))

    assert result == {
        "plan": [{"type": "generate", "input": "compare A and B"}],
        "current_step": 0,
        "step_results": [],
    }
