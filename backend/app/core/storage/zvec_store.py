"""Zvec vector store adapter.

The Python binding may not be stable in all environments yet. The adapter keeps
the interface in place and delegates to InMemoryVectorStore until a verified
binding is available.
"""

from app.core.storage.base import VectorHit
from app.core.storage.inmemory import InMemoryVectorStore


class ZvecVectorStore:
    """Zvec adapter with in-memory fallback for P0."""

    def __init__(self, path: str, dim: int) -> None:
        self.path = path
        self.dim = dim
        self._fallback = InMemoryVectorStore()

    async def add(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, object]],
    ) -> None:
        """Add vectors to the fallback index."""

        await self._fallback.add(ids, vectors, metadata)

    async def search(
        self,
        query: list[float],
        top_k: int,
        filter: dict[str, object] | None = None,
    ) -> list[VectorHit]:
        """Search the fallback index."""

        return await self._fallback.search(query, top_k, filter)

    async def delete(self, ids: list[str]) -> None:
        """Delete records from the fallback index."""

        await self._fallback.delete(ids)
