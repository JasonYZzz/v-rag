"""Planner graph node."""

import json
from typing import Any

from app.core.graph.registry import NodeDefinition
from app.core.graph.state import VragState


async def plan(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """Decompose the query into ordered plan-and-execute steps."""

    _ = config
    query = state["query"]
    prompt = (
        "Decompose the query into ordered steps. Each step: "
        '{"type": "retrieve"|"tool"|"generate", "input": "..."}. '
        'Reply JSON {"steps": [...]}. Query: '
        + query
    )
    raw = await services.llm.complete(prompt, system="You are a planning assistant.")
    steps = _parse_steps(raw, query)
    return {"plan": steps, "current_step": 0, "step_results": []}


def _parse_steps(raw: str, query: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [{"type": "generate", "input": query}]
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        return [{"type": "generate", "input": query}]
    parsed: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_type = step.get("type")
        if step_type not in {"retrieve", "tool", "generate"}:
            continue
        parsed.append({"type": step_type, "input": step.get("input", "")})
    return parsed or [{"type": "generate", "input": query}]


DEFN = NodeDefinition("planner", "Decompose query into steps", None, plan)
