"""P1 memory write placeholder."""

from typing import Any

from app.core.graph.state import VragState


async def memory_write(
    state: VragState, config: dict[str, Any], services: Any
) -> dict[str, Any]:
    """No-op memory write until P3 memory is implemented."""

    _ = (state, config, services)
    return {}
