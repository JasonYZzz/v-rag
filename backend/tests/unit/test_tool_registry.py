"""Self-hosted tool registry tests."""

import pytest

from app.core.tools.builtin import register_builtin_tools
from app.core.tools.registry import ToolDefinition, ToolRegistry


async def _noop(args: dict[str, object], services: object) -> dict[str, object]:
    _ = (args, services)
    return {"ok": True}


def test_tool_registry_registers_and_lists_tools() -> None:
    """Registry should expose only explicitly registered tools."""

    registry = ToolRegistry()
    registry.register(ToolDefinition("alpha", "Alpha tool", None, _noop))
    registry.register(ToolDefinition("beta", "Beta tool", None, _noop))

    assert registry.list() == ["alpha", "beta"]
    assert registry.get("alpha").description == "Alpha tool"


def test_tool_registry_rejects_duplicate_and_unknown_tools() -> None:
    """Duplicate and unknown tools should fail closed."""

    registry = ToolRegistry()
    registry.register(ToolDefinition("alpha", "Alpha tool", None, _noop))

    with pytest.raises(ValueError, match="tool already registered"):
        registry.register(ToolDefinition("alpha", "Duplicate", None, _noop))
    with pytest.raises(KeyError, match="unknown tool"):
        registry.get("missing")


async def test_builtin_stub_tools_return_deterministic_results() -> None:
    """Built-in tools should be safe deterministic P2-A stubs."""

    registry = ToolRegistry()
    register_builtin_tools(registry)

    assert registry.list() == ["query_db", "search_web"]
    search = await registry.get("search_web").execute({"q": "v-rag"}, object())
    db = await registry.get("query_db").execute({"sql": "select 1"}, object())

    assert search["tool"] == "search_web"
    assert "v-rag" in str(search["results"])
    assert db["tool"] == "query_db"
    assert db["rows"] == []
