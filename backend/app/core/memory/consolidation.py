"""Memory consolidation and forgetting orchestration."""

from typing import Any


async def consolidate(user_id: str | None, workspace_id: str, services: Any) -> dict[str, int]:
    """Merge similar facts, expire overdue records, and write an audit log."""

    merged = await services.merge_similar_facts(user_id, workspace_id)
    expired = await services.expire_overdue(user_id, workspace_id)
    await services.log_consolidation(user_id, {"merged": merged, "expired": expired})
    return {"merged": int(merged), "expired": int(expired)}


async def forget(filter_: dict[str, Any], services: Any) -> int:
    """Soft-delete memories and remove their vector indexes."""

    count = await services.mark_deleted(filter_)
    ids = filter_.get("ids", [])
    if ids:
        await services.memory_store.delete_memories([str(id_) for id_ in ids])
    return int(count)
