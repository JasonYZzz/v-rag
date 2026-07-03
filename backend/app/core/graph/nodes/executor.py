"""Executor graph node."""

from typing import Any

from app.core.graph.registry import NodeDefinition
from app.core.graph.state import VragState
from app.core.tools.registry import tool_registry


async def execute_step(state: VragState, config: dict[str, Any], services: Any) -> dict[str, Any]:
    """Execute the current plan step and advance the cursor."""

    _ = config
    plan_steps = state.get("plan", [])
    index = state.get("current_step", 0)
    if index >= len(plan_steps):
        return {}
    step = plan_steps[index]
    result = await _run_step(step, services)
    return {
        "current_step": index + 1,
        "step_results": [*state.get("step_results", []), result],
    }


async def _run_step(step: dict[str, Any], services: Any) -> dict[str, Any]:
    step_type = step.get("type")
    step_input = step.get("input", "")
    if step_type == "retrieve":
        hits = await services.retrieval.search(str(step_input), top_k=4)
        return {
            "step": step,
            "docs": [
                {
                    "chunk_id": hit.chunk_id,
                    "text": hit.text,
                    "score": hit.score,
                    "metadata": hit.metadata,
                }
                for hit in hits
            ],
        }
    if step_type == "tool":
        return {"step": step, "result": await _run_tool(step_input, services)}
    if step_type == "generate":
        text = await services.llm.complete(str(step_input))
        return {"step": step, "text": text}
    return {"step": step, "error": f"unknown step type: {step_type}"}


async def _run_tool(step_input: Any, services: Any) -> dict[str, Any]:
    tool_name = step_input.get("tool") if isinstance(step_input, dict) else str(step_input)
    args = step_input.get("args", {}) if isinstance(step_input, dict) else {}
    registry = getattr(services, "tools", tool_registry)
    try:
        tool = registry.get(str(tool_name))
    except KeyError:
        return {"error": f"unknown tool: {tool_name}"}
    return await tool.execute(args if isinstance(args, dict) else {}, services)


def should_continue(state: VragState) -> str:
    """Route back to executor until all plan steps are complete."""

    return "executor" if state.get("current_step", 0) < len(state.get("plan", [])) else "synthesizer"


DEFN = NodeDefinition("executor", "Execute plan steps", None, execute_step)
