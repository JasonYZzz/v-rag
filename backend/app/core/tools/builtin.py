"""Built-in deterministic P2-A tool stubs."""

from typing import Any

from app.core.tools.registry import ToolDefinition, ToolRegistry


async def search_web(args: dict[str, Any], services: Any) -> dict[str, Any]:
    """Return a deterministic stub web-search result."""

    _ = services
    query = str(args.get("q") or args.get("query") or "")
    return {
        "tool": "search_web",
        "query": query,
        "results": [{"title": "Stub search result", "snippet": f"Search result for {query}"}],
    }


async def query_db(args: dict[str, Any], services: Any) -> dict[str, Any]:
    """Return a deterministic stub database result."""

    _ = services
    return {"tool": "query_db", "query": str(args.get("sql") or args.get("query") or ""), "rows": []}


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Register P2-A built-in tools idempotently."""

    existing = set(registry.list())
    if "search_web" not in existing:
        registry.register(ToolDefinition("search_web", "Stub web search", None, search_web))
    if "query_db" not in existing:
        registry.register(ToolDefinition("query_db", "Stub database query", None, query_db))
