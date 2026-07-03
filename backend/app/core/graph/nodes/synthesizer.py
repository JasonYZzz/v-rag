"""Synthesizer graph node."""

from typing import Any

from app.core.graph.registry import NodeDefinition
from app.core.graph.state import VragState


async def synthesize(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """Synthesize step results into the final answer."""

    _ = config
    parts = [_stringify_result(result) for result in state.get("step_results", [])]
    summary = "\n---\n".join(parts)
    memory_context = "\n".join(str(block) for block in state.get("context_blocks", []) if block)
    final = await services.llm.complete(
        f"Synthesize a final answer from these step results.\n"
        f"Memory:\n{memory_context}\n\nResults:\n{summary}\n\nOriginal query: {state['query']}",
        system="You are the v-rag assistant.",
    )
    return {"generation": final}


def _stringify_result(result: dict[str, Any]) -> str:
    value = result.get("text") or result.get("result") or result
    return str(value)


DEFN = NodeDefinition("synthesizer", "Synthesize plan results", None, synthesize)
