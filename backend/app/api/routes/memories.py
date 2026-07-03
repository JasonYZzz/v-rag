"""Memory viewer backend API."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.memory.schemas import (
    MemoryFeedbackIn,
    MemoryFilter,
    MemoryOut,
    MemoryPatch,
    MemoryType,
    Scope,
    Status,
)
from app.core.memory.service import MemoryService
from app.deps import get_memory

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("")
async def list_memories_endpoint(
    memory: Annotated[MemoryService, Depends(get_memory)],
    memory_type: Annotated[MemoryType | None, Query(alias="type")] = None,
    user_id: str | None = None,
    workspace_id: str = "default",
    scope: Scope | None = None,
    status: Status | None = None,
    limit: int = 50,
) -> list[MemoryOut]:
    """List memories for the viewer."""

    return await memory.list_memories(
        MemoryFilter(
            memory_type=memory_type,
            user_id=user_id,
            workspace_id=workspace_id,
            scope=scope,
            status=status,
            limit=limit,
        )
    )


@router.patch("/{memory_id}")
async def update_memory_endpoint(
    memory_id: str,
    patch: MemoryPatch,
    memory: Annotated[MemoryService, Depends(get_memory)],
) -> MemoryOut:
    """Update a memory record."""

    return await memory.update_memory(memory_id, patch)


@router.post("/{memory_id}/feedback")
async def memory_feedback_endpoint(
    memory_id: str,
    feedback: MemoryFeedbackIn,
    memory: Annotated[MemoryService, Depends(get_memory)],
    memory_type: MemoryType = MemoryType.EVENT,
) -> dict[str, bool]:
    """Record memory feedback."""

    await memory.feedback(memory_id, memory_type, feedback)
    return {"ok": True}


@router.delete("")
async def forget_memories_endpoint(
    filter_: MemoryFilter,
    memory: Annotated[MemoryService, Depends(get_memory)],
) -> dict[str, int]:
    """Soft-delete memories."""

    return {"deleted": await memory.forget(filter_.model_dump(exclude_none=True))}
