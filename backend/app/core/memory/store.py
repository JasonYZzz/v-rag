"""Memory vector index built on the existing VectorStore abstraction."""

from typing import Any

from app.core.provider.base import EmbeddingProvider
from app.core.storage.base import VectorStore


class MemoryVectorIndex:
    """Index and search memories in the vector store."""

    def __init__(self, embedder: EmbeddingProvider, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store

    async def index_memories(
        self,
        ids: list[str],
        texts: list[str],
        metadata: list[dict[str, object]],
    ) -> None:
        """Embed and index memory records."""

        vectors = await self._embedder.embed(texts)
        await self._store.add(ids, vectors, metadata)

    async def search_memories(
        self,
        query: str,
        top_k: int,
        filter: dict[str, object] | None = None,
    ) -> list[dict[str, Any]]:
        """Search indexed memories and return dict hits."""

        vector = (await self._embedder.embed([query]))[0]
        hits = await self._store.search(vector, top_k=top_k, filter=filter)
        return [{"id": hit.id, "score": hit.score, "metadata": hit.metadata} for hit in hits]

    async def delete_memories(self, ids: list[str]) -> None:
        """Delete memory vectors."""

        await self._store.delete(ids)
