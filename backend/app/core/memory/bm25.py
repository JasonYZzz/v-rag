"""BM25 lexical recall for memory retrieval."""

from rank_bm25 import BM25Okapi


class BM25Index:
    """Small in-memory BM25 index for P3 memory recall."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._corpus: list[list[str]] = []

    def add(self, ids: list[str], texts: list[str]) -> None:
        """Add documents to the lexical index."""

        self._ids.extend(ids)
        self._corpus.extend(_tokenize(text) for text in texts)

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """Return top lexical matches."""

        if not self._corpus:
            return []
        bm25 = BM25Okapi(self._corpus)
        scores = bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self._ids, scores, strict=True), key=lambda item: item[1], reverse=True)
        return [(id_, float(score)) for id_, score in ranked[:top_k]]


def _tokenize(text: str) -> list[str]:
    return text.lower().split()

