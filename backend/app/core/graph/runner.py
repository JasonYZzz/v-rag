"""Graph runner."""

from typing import Any, cast

from app.core.graph.compiler import compile_graph
from app.core.graph.config import GraphConfig
from app.core.graph.state import VragState


async def run(config: GraphConfig, state: VragState, services: Any) -> VragState:
    """Compile and execute a graph with injected services."""

    compiled = compile_graph(config)
    return cast(VragState, await compiled.ainvoke(state, config={"configurable": {"services": services}}))
