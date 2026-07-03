"""Synthesizer node tests."""

from app.core.graph.nodes.synthesizer import synthesize
from app.core.graph.state import VragState


class FakeLLM:
    """Fake synthesis LLM."""

    def __init__(self) -> None:
        self.prompt = ""
        self.system = ""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Record the prompt and return a final answer."""

        self.prompt = prompt
        self.system = system
        return "final recommendation"


class Services:
    """Fake services."""

    def __init__(self) -> None:
        self.llm = FakeLLM()


async def test_synthesizer_combines_step_results_into_generation() -> None:
    """Synthesizer should ask the LLM to combine all step results."""

    services = Services()

    result = await synthesize(
        VragState(
            query="compare products",
            messages=[],
            step_results=[
                {"text": "A is fast"},
                {"result": {"summary": "B is cheap"}},
            ],
        ),
        {},
        services,
    )

    assert result == {"generation": "final recommendation"}
    assert "A is fast" in services.llm.prompt
    assert "B is cheap" in services.llm.prompt
    assert "Original query: compare products" in services.llm.prompt
    assert services.llm.system == "You are the v-rag assistant."
