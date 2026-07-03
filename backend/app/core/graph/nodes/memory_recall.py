"""P1 memory recall placeholder."""

from typing import Any

from app.core.graph.state import VragState


async def memory_recall(
    state: VragState, config: dict[str, Any], services: Any
) -> dict[str, Any]:
    """Return empty memory hits until P3 memory is implemented."""

    _ = (state, config, services)
    return {"memory_hits": []}
