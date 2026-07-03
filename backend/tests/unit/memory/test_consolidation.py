"""Memory consolidation tests."""

from app.core.memory.consolidation import consolidate, forget


class FakeMemoryStore:
    """Fake vector store deletion tracker."""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete_memories(self, ids: list[str]) -> None:
        self.deleted.extend(ids)


class Services:
    """Fake consolidation service methods."""

    def __init__(self) -> None:
        self.memory_store = FakeMemoryStore()
        self.logged: list[dict[str, object]] = []
        self.deleted_filter: dict[str, object] | None = None

    async def merge_similar_facts(self, user_id: str | None, workspace_id: str) -> int:
        assert user_id == "u1"
        assert workspace_id == "default"
        return 2

    async def expire_overdue(self, user_id: str | None, workspace_id: str) -> int:
        assert user_id == "u1"
        assert workspace_id == "default"
        return 3

    async def log_consolidation(self, user_id: str | None, details: dict[str, object]) -> None:
        assert user_id == "u1"
        self.logged.append(details)

    async def mark_deleted(self, filter_: dict[str, object]) -> int:
        self.deleted_filter = filter_
        return len(filter_["ids"])  # type: ignore[arg-type]


async def test_consolidate_merges_expires_and_logs() -> None:
    """Consolidation should merge similar facts, expire overdue records, and audit."""

    services = Services()

    result = await consolidate("u1", "default", services)

    assert result == {"merged": 2, "expired": 3}
    assert services.logged == [{"merged": 2, "expired": 3}]


async def test_forget_soft_deletes_and_removes_vectors() -> None:
    """Forget should soft-delete source records and delete vector indexes."""

    services = Services()

    count = await forget({"ids": ["m1", "m2"]}, services)

    assert count == 2
    assert services.deleted_filter == {"ids": ["m1", "m2"]}
    assert services.memory_store.deleted == ["m1", "m2"]
