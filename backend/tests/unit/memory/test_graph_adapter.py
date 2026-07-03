"""Graph adapter tests."""

from app.core.memory.graph_adapter import NoopGraphAdapter


async def test_noop_graph_adapter_accepts_fact_upsert_and_returns_no_neighbors() -> None:
    """Noop adapter should be safe for P3 while preserving the future interface."""

    adapter = NoopGraphAdapter()

    await adapter.upsert_fact({"subject": "team", "predicate": "uses", "object": "Spring"})

    assert await adapter.query_neighbors("team", depth=2) == []
