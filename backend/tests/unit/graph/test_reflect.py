"""Reflect node tests."""

from app.core.graph.nodes.reflect import MAX_REFLECT_ROUNDS, reflect, retry_target
from app.core.graph.state import Intent, VragState


class FakeLLM:
    """Fake judge LLM."""

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict
        self.prompt = ""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Record the prompt and return a verdict."""

        _ = system
        self.prompt = prompt
        return self.verdict


class Services:
    """Fake services."""

    def __init__(self, verdict: str) -> None:
        self.llm = FakeLLM(verdict)


async def test_reflect_records_good_verdict_without_retry() -> None:
    """Good answers should go to memory_write."""

    result = await reflect(
        VragState(query="q", generation="a", intent=Intent.KNOWLEDGE_QA, messages=[]),
        {},
        Services('{"quality": "good", "reason": "ok"}'),
    )

    assert result["reflection"] == {"quality": "good", "reason": "ok", "retry": False}
    assert result["reflect_rounds"] == 1
    assert retry_target(VragState(query="q", messages=[], **result)) == "memory_write"


async def test_reflect_routes_poor_quality_to_branch_retry_target() -> None:
    """Poor answers should retry the branch while under the round cap."""

    result = await reflect(
        VragState(query="q", generation="a", intent=Intent.KNOWLEDGE_QA, messages=[]),
        {},
        Services('{"quality": "poor", "reason": "missing evidence"}'),
    )
    complex_state = VragState(query="q", messages=[], intent=Intent.COMPLEX_TASK, **result)

    assert result["reflection"]["retry"] is True
    assert retry_target(VragState(query="q", messages=[], intent=Intent.KNOWLEDGE_QA, **result)) == "retrieve"
    assert retry_target(complex_state) == "planner"


async def test_reflect_caps_retry_rounds() -> None:
    """Reflect should stop retrying after MAX_REFLECT_ROUNDS."""

    result = await reflect(
        VragState(
            query="q",
            generation="a",
            intent=Intent.COMPLEX_TASK,
            reflect_rounds=MAX_REFLECT_ROUNDS,
            messages=[],
        ),
        {},
        Services('{"quality": "poor", "reason": "ignored"}'),
    )

    assert result == {
        "reflection": {"quality": "capped", "retry": False},
        "reflect_rounds": MAX_REFLECT_ROUNDS,
    }
    assert retry_target(VragState(query="q", messages=[], intent=Intent.COMPLEX_TASK, **result)) == "memory_write"
