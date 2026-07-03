"""P1 reflection placeholder."""

from typing import Any

from app.core.graph.state import VragState


async def reflect(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """Return a deterministic unchecked reflection marker."""

    _ = (state, config, services)
    return {"reflection": {"quality": "unchecked"}}
