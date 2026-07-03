"""Run trace API."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.db.models import RunTrace
from app.core.db.session import get_session_factory

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{trace_id}")
async def get_run_trace(trace_id: str) -> dict[str, Any]:
    """Return persisted node-level run trace."""

    async with get_session_factory()() as session:
        trace = await session.get(RunTrace, trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="run trace not found")
        return {
            "id": trace.id,
            "graph_config_id": trace.graph_config_id,
            "graph_version": trace.graph_version,
            "query": trace.query,
            "route_trace": trace.route_trace,
            "node_io": trace.node_io,
            "intent": trace.intent,
            "budget": trace.budget,
            "created_at": trace.created_at.isoformat() if trace.created_at else "",
        }
