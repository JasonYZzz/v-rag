"""Memory recall graph node."""

from typing import Any

from app.core.graph.state import VragState


async def memory_recall(
    state: VragState, config: dict[str, Any], services: Any
) -> dict[str, Any]:
    """Recall long-term memories through MemoryService."""

    result = await services.memory.recall(
        state["query"],
        top_k=int(config.get("top_k", 5)),
        scope=_scope_for_intent(state),
        user_id=state.get("user_id"),
        workspace_id=state.get("workspace_id", "default"),
    )
    return {"memory_hits": result["memories"], "context_blocks": [result["context"]]}


def _scope_for_intent(state: VragState) -> str:
    intent = state.get("intent")
    value = getattr(intent, "value", "")
    return {
        "knowledge_qa": "project",
        "complex_task": "user",
        "chitchat": "session",
    }.get(str(value), "user")
