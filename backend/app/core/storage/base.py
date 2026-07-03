"""Vector store protocol."""

from typing import NamedTuple, Protocol


class VectorHit(NamedTuple):
    """A single vector search hit."""

    id: str
    score: float
    metadata: dict[str, object]


class VectorStore(Protocol):
    """Vector index protocol."""

    async def add(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, object]],
    ) -> None:
        """Add vectors and metadata."""

    async def search(
        self,
        query: list[float],
        top_k: int,
        filter: dict[str, object] | None = None,
    ) -> list[VectorHit]:
        """Search top_k vectors with optional metadata equality filters."""

    async def delete(self, ids: list[str]) -> None:
        """Delete records by id."""
