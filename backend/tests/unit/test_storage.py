"""Storage abstraction tests."""

from app.core.storage.factory import build_vector_store


async def test_search_returns_by_cosine_similarity() -> None:
    """Search should return top_k results ordered by cosine similarity."""

    store = build_vector_store("inmemory")
    await store.add(
        ids=["a", "b", "c"],
        vectors=[[1.0, 0.0], [0.0, 1.0], [0.9, 0.1]],
        metadata=[{"doc": "1"}, {"doc": "2"}, {"doc": "1"}],
    )

    hits = await store.search([1.0, 0.0], top_k=2)

    assert hits[0].id == "a"
    assert hits[1].id == "c"


async def test_search_applies_metadata_filter() -> None:
    """Search should apply metadata equality filters."""

    store = build_vector_store("inmemory")
    await store.add(
        ids=["a", "b"],
        vectors=[[1.0, 0.0], [1.0, 0.0]],
        metadata=[{"doc": "1"}, {"doc": "2"}],
    )

    hits = await store.search([1.0, 0.0], top_k=5, filter={"doc": "2"})

    assert [hit.id for hit in hits] == ["b"]


async def test_delete_removes_records() -> None:
    """Delete should remove indexed records."""

    store = build_vector_store("inmemory")
    await store.add(ids=["a"], vectors=[[1.0]], metadata=[{}])

    await store.delete(["a"])

    assert await store.search([1.0], top_k=5) == []
