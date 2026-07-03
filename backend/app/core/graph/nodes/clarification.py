"""Clarification graph node."""

from typing import Any

from app.core.graph.state import VragState


async def clarification(
    state: VragState, config: dict[str, Any], services: Any
) -> dict[str, Any]:
    """Ask the user for missing information."""

    _ = (state, services)
    return {
        "generation": config.get(
            "message",
            "需要更多信息: 能否说明具体的知识库/对象/时间范围?",
        )
    }
