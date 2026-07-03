"""Memory write path with Policy Gate."""

from dataclasses import dataclass
from typing import Any

from app.core.memory.schemas import MemoryIn, SourceType


@dataclass(frozen=True)
class WriteDecision:
    """Policy Gate decision."""

    accept: bool
    reason: str
    importance: float
    memory_type: str


def importance_score(content: str, source_type: SourceType) -> float:
    """Heuristic long-term value score."""

    base = {
        SourceType.USER: 0.7,
        SourceType.TOOL: 0.6,
        SourceType.DOCUMENT: 0.5,
        SourceType.LLM_GENERATED: 0.2,
    }[source_type]
    return min(1.0, base + min(0.2, len(content) / 1000))


def policy_gate(decision_input: MemoryIn, importance: float) -> WriteDecision:
    """Accept or reject a memory candidate before persistence."""

    if decision_input.source_type is SourceType.LLM_GENERATED:
        return WriteDecision(
            False,
            "reject: llm_generated not written as fact",
            importance,
            "",
        )
    if importance < 0.3:
        return WriteDecision(False, "reject: low long-term value", importance, "")
    memory_type = "fact" if decision_input.subject and decision_input.predicate else "event"
    return WriteDecision(True, "accepted", importance, memory_type)


async def write(input_: MemoryIn, services: Any) -> dict[str, Any]:
    """Run candidate -> policy -> PG persistence -> vector index."""

    importance = importance_score(input_.content, input_.source_type)
    decision = policy_gate(input_, importance)
    if not decision.accept:
        return {"accepted": False, "reason": decision.reason}
    memory_id = await services.memory_persist(input_, decision.memory_type, importance)
    await services.memory_store.index_memories(
        [memory_id],
        [input_.content],
        [
            {
                "memory_type": decision.memory_type,
                "scope": input_.scope.value,
                "workspace_id": input_.workspace_id,
            }
        ],
    )
    return {
        "accepted": True,
        "memory_id": memory_id,
        "memory_type": decision.memory_type,
        "importance": importance,
    }
