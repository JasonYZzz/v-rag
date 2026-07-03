"""Retrieval engine tests."""

from app.core.retrieval.engine import RetrievalEngine
from app.core.storage.factory import build_vector_store


class FakeEmbedder:
    """Deterministic embedder based on character counts."""

    @property
    def dim(self) -> int:
        """Return fake vector dimension."""

        return 4

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts into character-count vectors."""

        def vector(text: str) -> list[float]:
            return [float(text.count(char)) for char in "abcd"]

        return [vector(text) for text in texts]


async def test_search_returns_indexed_chunk_text() -> None:
    """Search should return indexed chunk text."""

    embedder = FakeEmbedder()
    engine = RetrievalEngine(embedder, build_vector_store("inmemory"))
    await engine.index(
        [
            (
                "c1",
                (await embedder.embed(["abc"]))[0],
                {"doc": "d1", "text": "hello world"},
            ),
        ]
    )

    hits = await engine.search("abc", top_k=1)

    assert len(hits) == 1
    assert hits[0].chunk_id == "c1"
    assert hits[0].text == "hello world"
