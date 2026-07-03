"""Unsupported request graph node."""

from typing import Any

from app.core.graph.state import VragState


async def unsupported(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """Return a safe unsupported-request response."""

    _ = (state, services)
    return {"generation": config.get("message", "该请求暂不支持或超出允许范围。")}
