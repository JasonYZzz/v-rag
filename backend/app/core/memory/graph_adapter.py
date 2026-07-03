"""Graph-ready adapter interface for semantic memory facts."""

from typing import Protocol


class GraphAdapter(Protocol):
    """Future graph adapter for Cognee/Graphiti/graph stores."""

    async def upsert_fact(self, fact: dict[str, object]) -> None:
        """Export or upsert a semantic fact."""

    async def query_neighbors(self, subject: str, depth: int = 1) -> list[dict[str, object]]:
        """Query graph neighbors for a subject."""


class NoopGraphAdapter:
    """P3 placeholder adapter."""

    async def upsert_fact(self, fact: dict[str, object]) -> None:
        """Ignore fact upserts."""

        _ = fact

    async def query_neighbors(self, subject: str, depth: int = 1) -> list[dict[str, object]]:
        """Return no graph neighbors."""

        _ = (subject, depth)
        return []

