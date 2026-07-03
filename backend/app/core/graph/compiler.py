"""Compile controlled graph_config into LangGraph executables."""

import inspect
from collections.abc import Awaitable, Callable, Hashable
from functools import lru_cache
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.core.graph.config import GraphConfig, GraphEdgeSpec, GraphNodeSpec
from app.core.graph.nodes import register_all
from app.core.graph.registry import NodeDefinition, registry
from app.core.graph.state import Intent, VragState

MAX_NODES = 30
MAX_REFLECT_ROUNDS = 2

CompiledGraph = Any


class GraphSafetyError(ValueError):
    """Graph structure is unsafe or unsupported."""


def validate(config: GraphConfig) -> None:
    """Validate graph structure and node whitelist."""

    register_all()
    if len(config.nodes) > MAX_NODES:
        raise GraphSafetyError(f"too many nodes: {len(config.nodes)} > {MAX_NODES}")
    for node in config.nodes:
        if not registry.has(node.type):
            raise GraphSafetyError(f"node type not in registry: {node.type}")
    _check_reachable(config)
    _check_terminates(config)
    _check_conditions(config)


def _check_reachable(config: GraphConfig) -> None:
    adjacency = _adjacency(config.edges)
    seen = _walk_forward(config.entry, adjacency)
    missing = sorted({node.id for node in config.nodes} - seen)
    if missing:
        raise GraphSafetyError(f"unreachable nodes: {', '.join(missing)}")


def _check_terminates(config: GraphConfig) -> None:
    reverse: dict[str, list[str]] = {node.id: [] for node in config.nodes}
    for edge in config.edges:
        reverse.setdefault(edge.dst, []).append(edge.src)
    can_exit: set[str] = set(config.exits)
    frontier = list(config.exits)
    while frontier:
        current = frontier.pop()
        for parent in reverse.get(current, []):
            if parent not in can_exit:
                can_exit.add(parent)
                frontier.append(parent)
    missing = sorted({node.id for node in config.nodes} - can_exit)
    if missing:
        raise GraphSafetyError(f"nodes cannot reach exit: {', '.join(missing)}")


def _check_conditions(config: GraphConfig) -> None:
    for edge in config.edges:
        if edge.condition is None:
            continue
        field, value = _parse_condition(edge.condition)
        if not field or not value:
            raise GraphSafetyError(f"invalid condition: {edge.condition}")


def _adjacency(edges: list[GraphEdgeSpec]) -> dict[str, list[str]]:
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.src, []).append(edge.dst)
    return adjacency


def _walk_forward(start: str, adjacency: dict[str, list[str]]) -> set[str]:
    seen = {start}
    frontier = [start]
    while frontier:
        current = frontier.pop()
        for child in adjacency.get(current, []):
            if child not in seen:
                seen.add(child)
                frontier.append(child)
    return seen


@lru_cache(maxsize=64)
def _compile_cached(config_json: str) -> CompiledGraph:
    config = GraphConfig.model_validate_json(config_json)
    validate(config)
    graph = StateGraph(VragState)
    nodes_by_id = {node.id: node for node in config.nodes}
    for node in config.nodes:
        defn = registry.get(node.type)
        graph.add_node(node.id, cast(Any, _wrap(node, defn)))
    graph.add_edge(START, config.entry)

    edges_by_source: dict[str, list[GraphEdgeSpec]] = {}
    for edge in config.edges:
        edges_by_source.setdefault(edge.src, []).append(edge)
    for source, edges in edges_by_source.items():
        conditional = [edge for edge in edges if edge.condition]
        unconditional = [edge for edge in edges if not edge.condition]
        if conditional:
            destinations: dict[Hashable, str] = {edge.dst: edge.dst for edge in edges}
            destinations[END] = END
            graph.add_conditional_edges(source, _make_router(conditional, unconditional), destinations)
        else:
            for edge in unconditional:
                graph.add_edge(edge.src, edge.dst)

    for exit_id in config.exits:
        if exit_id in nodes_by_id:
            graph.add_edge(exit_id, END)
    return graph.compile()


def compile_graph(config: GraphConfig) -> CompiledGraph:
    """Compile a graph config with an LRU cache."""

    return _compile_cached(config.model_dump_json(by_alias=True))


def _wrap(
    node: GraphNodeSpec, defn: NodeDefinition
) -> Callable[[VragState, RunnableConfig], Awaitable[dict[str, Any]]]:
    async def wrapped(state: VragState, config: RunnableConfig) -> dict[str, Any]:
        configurable = config.get("configurable", {})
        services = configurable.get("services")
        if defn.config_schema is not None:
            defn.config_schema.model_validate(node.config)
        before = _state_summary(state)
        result = defn.execute(state, node.config, services)
        patch = await result if inspect.isawaitable(result) else result
        entry = {"node_id": node.id, "type": node.type, "input": before, "output": patch}
        return {**patch, "node_io": [*state.get("node_io", []), entry]}

    return wrapped


def _make_router(
    conditional: list[GraphEdgeSpec], unconditional: list[GraphEdgeSpec]
) -> Callable[[VragState], str]:
    def route(state: VragState) -> str:
        for edge in conditional:
            if edge.condition and _condition_matches(state, edge.condition):
                return edge.dst
        if unconditional:
            return unconditional[0].dst
        return END

    return route


def _condition_matches(state: VragState, condition: str) -> bool:
    field, expected = _parse_condition(condition)
    actual = state.get(cast(Any, field))
    if isinstance(actual, Intent):
        actual = actual.value
    return str(actual) == expected


def _parse_condition(condition: str) -> tuple[str, str]:
    if condition.count("=") != 1:
        raise GraphSafetyError(f"invalid condition: {condition}")
    field, expected = (part.strip() for part in condition.split("=", 1))
    if not field.replace("_", "").isalnum() or not expected:
        raise GraphSafetyError(f"invalid condition: {condition}")
    return field, expected


def _state_summary(state: VragState) -> dict[str, Any]:
    intent = state.get("intent")
    return {
        "query": state.get("query"),
        "intent": intent.value if isinstance(intent, Intent) else None,
        "confidence": state.get("confidence"),
        "retrieved_docs_count": len(state.get("retrieved_docs", [])),
        "has_generation": bool(state.get("generation")),
    }
