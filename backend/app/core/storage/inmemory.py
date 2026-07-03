"""In-memory vector store for tests and zero-dependency startup."""

import math

from app.core.storage.base import VectorHit


class InMemoryVectorStore:
    """Naive cosine-similarity vector store."""

    def __init__(self) -> None:
        self._records: dict[str, tuple[list[float], dict[str, object]]] = {}

    async def add(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, object]],
    ) -> None:
        """Add or replace vectors."""

        for id_, vector, meta in zip(ids, vectors, metadata, strict=True):
            self._records[id_] = (vector, meta)

    async def search(
        self,
        query: list[float],
        top_k: int,
        filter: dict[str, object] | None = None,
    ) -> list[VectorHit]:
        """Search vectors by cosine similarity."""

        scored: list[tuple[float, str, dict[str, object]]] = []
        for id_, (vector, meta) in self._records.items():
            if filter and not all(meta.get(key) == value for key, value in filter.items()):
                continue
            scored.append((_cosine(query, vector), id_, meta))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [VectorHit(id=id_, score=score, metadata=meta) for score, id_, meta in scored[:top_k]]

    async def delete(self, ids: list[str]) -> None:
        """Delete records by id."""

        for id_ in ids:
            self._records.pop(id_, None)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
