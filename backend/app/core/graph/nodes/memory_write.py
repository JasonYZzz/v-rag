"""Memory write graph node."""

from typing import Any

from app.core.graph.state import VragState
from app.core.memory.schemas import MemoryIn, Scope, SourceType


async def memory_write(
    state: VragState, config: dict[str, Any], services: Any
) -> dict[str, Any]:
    """Persist user/document-sourced memory candidates."""

    _ = config
    writes: list[dict[str, Any]] = []
    workspace_id = state.get("workspace_id", "default")
    user_id = state.get("user_id")
    writes.append(
        await services.memory.remember(
            MemoryIn(
                content=state["query"],
                user_id=user_id,
                workspace_id=workspace_id,
                scope=Scope.USER,
                source_type=SourceType.USER,
            )
        )
    )
    for doc in state.get("retrieved_docs", []):
        text = str(doc.get("text", "")).strip()
        if not text:
            continue
        writes.append(
            await services.memory.remember(
                MemoryIn(
                    content=text,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    scope=Scope.PROJECT,
                    source_type=SourceType.DOCUMENT,
                )
            )
        )
    return {"memory_writes": writes}
