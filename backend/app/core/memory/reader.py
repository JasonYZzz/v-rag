"""Memory read path with Memory Gate and Context Builder."""

from typing import Any


async def recall(
    query: str,
    services: Any,
    *,
    top_k: int = 5,
    scope: str | None = None,
    workspace_id: str = "default",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Hybrid recall plus gating and compact context construction."""

    vector_hits = await services.memory_store.search_memories(
        query,
        top_k=top_k * 2,
        filter={"workspace_id": workspace_id},
    )
    bm25_hits = services.bm25.search(query, top_k=top_k * 2)
    recent = await services.memory_recent_episodic(user_id, workspace_id, limit=top_k)
    merged = await _merge_and_rerank(vector_hits, bm25_hits, recent, services)
    gated = _memory_gate(merged, query, scope, user_id)
    selected = gated[:top_k]
    return {"memories": selected, "context": _build_context(selected)}


async def _merge_and_rerank(
    vector_hits: list[dict[str, Any]],
    bm25_hits: list[tuple[str, float]],
    recent: list[dict[str, Any]],
    services: Any,
) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    for hit in vector_hits:
        id_ = str(hit["id"])
        scores[id_] = max(scores.get(id_, 0.0), float(hit.get("score", 0.0)))
    for id_, score in bm25_hits:
        scores[id_] = max(scores.get(id_, 0.0), float(score))
    records = await services.memory_lookup(list(scores))
    by_id = {str(record["id"]): {**record, "_score": scores[str(record["id"])]} for record in records}
    for item in recent:
        id_ = str(item["id"])
        by_id[id_] = {**item, "_score": max(float(item.get("_score", 0.0)), by_id.get(id_, {}).get("_score", 0.0))}
    return sorted(by_id.values(), key=lambda item: float(item.get("_score", 0.0)), reverse=True)


def _memory_gate(
    candidates: list[dict[str, Any]],
    query: str,
    scope: str | None,
    user_id: str | None,
) -> list[dict[str, Any]]:
    """Filter by lifecycle/scope and demote sensitive memories."""

    _ = (query, user_id)
    out: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("status") not in (None, "active"):
            continue
        if scope and candidate.get("scope") != scope:
            continue
        item = dict(candidate)
        if item.get("sensitivity") in ("private", "sensitive"):
            item["_score"] = float(item.get("_score", 0.0)) * 0.5
        out.append(item)
    return _dedupe_conflicts(out)


def _dedupe_conflicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_fact_key: dict[tuple[str, str], dict[str, Any]] = {}
    passthrough: list[dict[str, Any]] = []
    for item in items:
        if item.get("memory_type") == "fact" and item.get("subject") and item.get("predicate"):
            key = (str(item["subject"]), str(item["predicate"]))
            current = by_fact_key.get(key)
            if current is None or str(item.get("created_at", "")) >= str(current.get("created_at", "")):
                by_fact_key[key] = item
        else:
            passthrough.append(item)
    deduped = [*passthrough, *by_fact_key.values()]
    return sorted(deduped, key=lambda item: float(item.get("_score", 0.0)), reverse=True)


def _build_context(memories: list[dict[str, Any]]) -> str:
    """Build a compact memory context block."""

    return "\n".join(f"- [{memory.get('memory_type')}] {_memory_text(memory)}" for memory in memories)


def _memory_text(memory: dict[str, Any]) -> str:
    if memory.get("content"):
        return str(memory["content"])
    if memory.get("subject") and memory.get("predicate"):
        return f"{memory.get('subject')} {memory.get('predicate')} {memory.get('object', '')}".strip()
    return ""
