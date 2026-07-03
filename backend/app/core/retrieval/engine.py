"""Retrieval engine orchestration."""

from dataclasses import dataclass

from app.core.provider.base import EmbeddingProvider
from app.core.storage.base import VectorHit, VectorStore


@dataclass(frozen=True)
class RetrievedChunk:
    """A retrieved chunk with citation metadata."""

    chunk_id: str
    text: str
    score: float
    metadata: dict[str, object]


class RetrievalEngine:
    """Embed query, search vector store, and attach chunk text."""

    def __init__(self, embedder: EmbeddingProvider, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store
        self._texts: dict[str, str] = {}

    async def index(self, chunks: list[tuple[str, list[float], dict[str, object]]]) -> None:
        """Index embedded chunks as (chunk_id, vector, metadata)."""

        ids = [chunk[0] for chunk in chunks]
        vectors = [chunk[1] for chunk in chunks]
        metadata = [
            {key: value for key, value in chunk[2].items() if key != "text"} for chunk in chunks
        ]
        for chunk_id, _vector, meta in chunks:
            text = meta.get("text")
            if isinstance(text, str):
                self._texts[chunk_id] = text
        await self._store.add(ids, vectors, metadata)

    async def search(
        self,
        query: str,
        top_k: int = 4,
        filter: dict[str, object] | None = None,
        text_lookup: dict[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        """Search for chunks matching query."""

        query_vector = (await self._embedder.embed([query]))[0]
        hits: list[VectorHit] = await self._store.search(query_vector, top_k, filter)
        lookup = text_lookup or self._texts
        return [
            RetrievedChunk(
                chunk_id=hit.id,
                text=lookup.get(hit.id, ""),
                score=hit.score,
                metadata=hit.metadata,
            )
            for hit in hits
        ]
