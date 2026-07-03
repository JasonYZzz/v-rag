"""Graph compiler safety and execution tests."""

from typing import Any

import pytest

from app.core.graph.compiler import GraphSafetyError, compile_graph, validate
from app.core.graph.config import GraphConfig
from app.core.graph.state import Intent, VragState


class Services:
    """Placeholder services for graph execution."""


def _config(raw: dict[str, Any]) -> GraphConfig:
    return GraphConfig.model_validate(raw)


def test_validate_rejects_unregistered_node_type() -> None:
    """Compiler safety should reject node types outside the registry."""

    config = _config(
        {
            "entry": "x",
            "nodes": [{"id": "x", "type": "missing"}],
            "edges": [],
            "exits": ["x"],
        }
    )

    with pytest.raises(GraphSafetyError, match="node type not in registry"):
        validate(config)


def test_validate_rejects_unreachable_nodes() -> None:
    """All declared nodes should be reachable from entry."""

    config = _config(
        {
            "entry": "classifier",
            "nodes": [
                {"id": "classifier", "type": "classifier"},
                {"id": "generate", "type": "generate"},
            ],
            "edges": [],
            "exits": ["classifier"],
        }
    )

    with pytest.raises(GraphSafetyError, match="unreachable nodes"):
        validate(config)


def test_validate_rejects_nodes_without_exit_path() -> None:
    """Every node should be able to terminate at an exit."""

    config = _config(
        {
            "entry": "classifier",
            "nodes": [
                {"id": "classifier", "type": "classifier"},
                {"id": "generate", "type": "generate"},
            ],
            "edges": [{"from": "classifier", "to": "generate"}],
            "exits": ["classifier"],
        }
    )

    with pytest.raises(GraphSafetyError, match="cannot reach exit"):
        validate(config)


def test_validate_rejects_too_many_nodes() -> None:
    """Graph size should be bounded."""

    nodes = [{"id": f"n{i}", "type": "generate"} for i in range(31)]
    edges = [{"from": f"n{i}", "to": f"n{i + 1}"} for i in range(30)]
    config = _config({"entry": "n0", "nodes": nodes, "edges": edges, "exits": ["n30"]})

    with pytest.raises(GraphSafetyError, match="too many nodes"):
        validate(config)


async def test_compile_and_run_routes_conditionally_and_records_node_io() -> None:
    """Compiled graph should execute condition edges and append node trace."""

    config = _config(
        {
            "entry": "memory_recall",
            "nodes": [
                {"id": "memory_recall", "type": "memory_recall"},
                {"id": "generate", "type": "generate"},
                {"id": "clarify", "type": "clarification"},
            ],
            "edges": [
                {"from": "memory_recall", "to": "generate", "condition": "intent=knowledge_qa"},
                {
                    "from": "memory_recall",
                    "to": "clarify",
                    "condition": "intent=clarification_needed",
                },
            ],
            "exits": ["generate", "clarify"],
        }
    )

    compiled = compile_graph(config)
    final = await compiled.ainvoke(
        VragState(query="q", intent=Intent.CLARIFICATION, messages=[]),
        config={"configurable": {"services": Services()}},
    )

    assert final["generation"].startswith("需要更多信息")
    assert [entry["node_id"] for entry in final["node_io"]] == ["memory_recall", "clarify"]
    assert compile_graph(config) is compiled
