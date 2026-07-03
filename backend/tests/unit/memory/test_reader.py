"""Memory reader tests."""

from app.core.memory.reader import _build_context, _memory_gate, recall


class FakeMemoryStore:
    """Fake vector memory store."""

    async def search_memories(
        self,
        query: str,
        top_k: int,
        filter: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        _ = (query, top_k, filter)
        return [
            {"id": "m1", "score": 0.9, "metadata": {"workspace_id": "default"}},
            {"id": "m2", "score": 0.2, "metadata": {"workspace_id": "default"}},
        ]


class FakeBM25:
    """Fake lexical memory index."""

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        _ = (query, top_k)
        return [("m2", 0.8), ("m3", 0.4)]


class Services:
    """Fake reader services."""

    def __init__(self) -> None:
        self.memory_store = FakeMemoryStore()
        self.bm25 = FakeBM25()

    async def memory_recent_episodic(
        self,
        user_id: str | None,
        workspace_id: str,
        limit: int,
    ) -> list[dict[str, object]]:
        _ = (user_id, workspace_id, limit)
        return [{"id": "m4", "content": "recent user memory", "_score": 0.3}]

    async def memory_lookup(self, ids: list[str]) -> list[dict[str, object]]:
        records = {
            "m1": {
                "id": "m1",
                "content": "user prefers python",
                "memory_type": "event",
                "scope": "user",
                "status": "active",
                "workspace_id": "default",
                "importance": 0.9,
            },
            "m2": {
                "id": "m2",
                "content": "team uses spring",
                "memory_type": "event",
                "scope": "project",
                "status": "active",
                "workspace_id": "default",
                "importance": 0.7,
            },
            "m3": {
                "id": "m3",
                "content": "deleted memory",
                "memory_type": "event",
                "scope": "user",
                "status": "deleted",
                "workspace_id": "default",
                "importance": 1.0,
            },
        }
        return [records[id_] for id_ in ids if id_ in records]


async def test_recall_merges_vector_bm25_recent_and_builds_context() -> None:
    """Recall should combine all retrieval sources and return gated context."""

    result = await recall("tech stack", Services(), top_k=3, scope=None, user_id="u1")

    assert [memory["id"] for memory in result["memories"]] == ["m1", "m2", "m4"]
    assert "- [event] user prefers python" in result["context"]
    assert "deleted memory" not in result["context"]


def test_memory_gate_filters_scope_status_and_demotes_sensitive() -> None:
    """Memory Gate should enforce scope/status and demote sensitive candidates."""

    gated = _memory_gate(
        [
            {"id": "active", "scope": "user", "status": "active", "_score": 0.8},
            {"id": "deleted", "scope": "user", "status": "deleted", "_score": 1.0},
            {"id": "project", "scope": "project", "status": "active", "_score": 1.0},
            {
                "id": "sensitive",
                "scope": "user",
                "status": "active",
                "sensitivity": "sensitive",
                "_score": 0.8,
            },
        ],
        "q",
        "user",
        "u1",
    )

    assert [item["id"] for item in gated] == ["active", "sensitive"]
    assert gated[1]["_score"] == 0.4


def test_memory_gate_dedupes_conflicting_facts_by_newest() -> None:
    """Fact conflicts should keep the newest subject/predicate candidate."""

    gated = _memory_gate(
        [
            {
                "id": "old",
                "memory_type": "fact",
                "subject": "user",
                "predicate": "prefers",
                "object": "Java",
                "created_at": "2026-01-01",
                "status": "active",
                "_score": 1.0,
            },
            {
                "id": "new",
                "memory_type": "fact",
                "subject": "user",
                "predicate": "prefers",
                "object": "Python",
                "created_at": "2026-07-03",
                "status": "active",
                "_score": 0.7,
            },
        ],
        "q",
        None,
        "u1",
    )

    assert [item["id"] for item in gated] == ["new"]


def test_build_context_uses_compact_memory_blocks() -> None:
    """Context Builder should emit compact typed memory lines."""

    assert _build_context(
        [
            {"memory_type": "event", "content": "user prefers Python"},
            {"memory_type": "fact", "subject": "team", "predicate": "uses", "object": "Spring"},
        ]
    ) == "- [event] user prefers Python\n- [fact] team uses Spring"
