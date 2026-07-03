"""Memory graph node tests."""

from app.core.graph.nodes.memory_recall import memory_recall
from app.core.graph.nodes.memory_write import memory_write
from app.core.graph.state import Intent, VragState
from app.core.memory.schemas import MemoryIn


class FakeMemory:
    """Fake MemoryService for graph node tests."""

    def __init__(self) -> None:
        self.recall_calls: list[dict[str, object]] = []
        self.remembered: list[MemoryIn] = []

    async def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        scope: str | None = None,
        user_id: str | None = None,
        workspace_id: str = "default",
    ) -> dict[str, object]:
        self.recall_calls.append(
            {
                "query": query,
                "top_k": top_k,
                "scope": scope,
                "user_id": user_id,
                "workspace_id": workspace_id,
            }
        )
        return {"memories": [{"content": "remembered"}], "context": "memory context"}

    async def remember(self, input_: MemoryIn) -> dict[str, object]:
        self.remembered.append(input_)
        return {"accepted": True, "memory_id": f"m{len(self.remembered)}"}


class Services:
    """Fake graph services."""

    def __init__(self) -> None:
        self.memory = FakeMemory()


async def test_memory_recall_selects_scope_by_intent() -> None:
    """memory_recall should pass intent-aware scope to MemoryService."""

    services = Services()

    result = await memory_recall(
        VragState(
            query="what stack",
            intent=Intent.KNOWLEDGE_QA,
            user_id="u1",
            workspace_id="w1",
            messages=[],
        ),
        {"top_k": 3},
        services,
    )

    assert result == {"memory_hits": [{"content": "remembered"}], "context_blocks": ["memory context"]}
    assert services.memory.recall_calls == [
        {
            "query": "what stack",
            "top_k": 3,
            "scope": "project",
            "user_id": "u1",
            "workspace_id": "w1",
        }
    ]


async def test_memory_write_writes_user_and_document_sources_but_not_generation() -> None:
    """memory_write should never persist generated answer text as a fact."""

    services = Services()

    result = await memory_write(
        VragState(
            query="I prefer Python",
            user_id="u1",
            workspace_id="w1",
            retrieved_docs=[{"text": "Document says team uses Spring"}],
            generation="Assistant says use Rust",
            messages=[],
        ),
        {},
        services,
    )

    assert result["memory_writes"] == [
        {"accepted": True, "memory_id": "m1"},
        {"accepted": True, "memory_id": "m2"},
    ]
    assert [item.content for item in services.memory.remembered] == [
        "I prefer Python",
        "Document says team uses Spring",
    ]
    assert [item.source_type.value for item in services.memory.remembered] == ["user", "document"]
