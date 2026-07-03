"""Reflect graph node with LLM-as-judge retry decisions."""

import json
from typing import Any

from app.core.graph.state import VragState

MAX_REFLECT_ROUNDS = 2


async def reflect(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """Judge generation quality and record capped retry state."""

    _ = config
    rounds = state.get("reflect_rounds", 0)
    if rounds >= MAX_REFLECT_ROUNDS:
        return {"reflection": {"quality": "capped", "retry": False}, "reflect_rounds": rounds}
    verdict = await services.llm.complete(
        'Is this answer good for the query? Reply JSON {"quality": "good"|"poor", "reason": "..."}.\n'
        f"Query: {state['query']}\nAnswer: {state.get('generation', '')}"
    )
    data = _parse_verdict(verdict)
    data["retry"] = data.get("quality") == "poor" and rounds + 1 < MAX_REFLECT_ROUNDS
    return {"reflection": data, "reflect_rounds": rounds + 1}


def retry_target(state: VragState) -> str:
    """Return the branch retry target for poor-quality answers."""

    reflection = state.get("reflection") or {}
    if reflection.get("quality") == "poor" and state.get("reflect_rounds", 0) < MAX_REFLECT_ROUNDS:
        intent = state.get("intent")
        intent_value = getattr(intent, "value", intent)
        if intent_value == "knowledge_qa":
            return "retrieve"
        if intent_value == "complex_task":
            return "planner"
    return "memory_write"


def _parse_verdict(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"quality": "good", "reason": "invalid judge json"}
    quality = data.get("quality")
    if quality not in {"good", "poor"}:
        quality = "good"
    return {"quality": quality, "reason": str(data.get("reason", ""))}
