"""Memory BM25 and vector index tests."""

from app.core.memory.bm25 import BM25Index
from app.core.memory.store import MemoryVectorIndex
from app.core.storage.inmemory import InMemoryVectorStore


class FakeEmbedder:
    """Deterministic fake embedder."""

    @property
    def dim(self) -> int:
        return 3

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts into tiny keyword vectors."""

        vectors: list[list[float]] = []
        for text in texts:
            normalized = text.lower()
            vectors.append(
                [
                    1.0 if "python" in normalized else 0.0,
                    1.0 if "spring" in normalized else 0.0,
                    1.0 if "design" in normalized else 0.0,
                ]
            )
        return vectors


def test_bm25_returns_relevant_memory_first() -> None:
    """BM25 should rank lexical matches above unrelated memories."""

    index = BM25Index()
    index.add(["m1", "m2"], ["user prefers python", "team uses spring"])

    results = index.search("python preference", top_k=2)

    assert results[0][0] == "m1"
    assert results[0][1] >= results[1][1]


async def test_memory_vector_index_add_search_and_delete() -> None:
    """MemoryVectorIndex should reuse the storage abstraction with metadata filters."""

    vector_index = MemoryVectorIndex(FakeEmbedder(), InMemoryVectorStore())
    await vector_index.index_memories(
        ["m1", "m2"],
        ["user prefers python", "team uses spring"],
        [
            {"memory_type": "event", "workspace_id": "default"},
            {"memory_type": "event", "workspace_id": "other"},
        ],
    )

    hits = await vector_index.search_memories(
        "python",
        top_k=5,
        filter={"workspace_id": "default"},
    )
    assert [hit["id"] for hit in hits] == ["m1"]
    assert hits[0]["metadata"]["memory_type"] == "event"

    await vector_index.delete_memories(["m1"])
    assert (
        await vector_index.search_memories("python", top_k=5, filter={"workspace_id": "default"})
        == []
    )
