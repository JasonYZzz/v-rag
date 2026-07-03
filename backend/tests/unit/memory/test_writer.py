"""Memory writer tests."""


from app.core.memory.schemas import MemoryIn, Scope, SourceType
from app.core.memory.writer import policy_gate, write


class FakeMemoryStore:
    """Fake vector memory store."""

    def __init__(self) -> None:
        self.indexed: list[tuple[list[str], list[str], list[dict[str, object]]]] = []

    async def index_memories(
        self,
        ids: list[str],
        texts: list[str],
        metadata: list[dict[str, object]],
    ) -> None:
        self.indexed.append((ids, texts, metadata))


class Services:
    """Fake writer services."""

    def __init__(self) -> None:
        self.memory_store = FakeMemoryStore()
        self.persisted: list[tuple[MemoryIn, str, float]] = []

    async def memory_persist(self, input_: MemoryIn, memory_type: str, importance: float) -> str:
        self.persisted.append((input_, memory_type, importance))
        return f"{memory_type}-1"


def test_policy_gate_accepts_allowed_sources_and_classifies_type() -> None:
    """Policy gate should accept trusted sources and classify fact/event."""

    event = policy_gate(MemoryIn(content="I prefer Python"), 0.7)
    fact = policy_gate(
        MemoryIn(
            content="user prefers Python",
            source_type=SourceType.DOCUMENT,
            subject="user",
            predicate="prefers",
            object="Python",
        ),
        0.6,
    )

    assert event.accept is True
    assert event.memory_type == "event"
    assert fact.accept is True
    assert fact.memory_type == "fact"


def test_policy_gate_rejects_llm_generated_and_low_value() -> None:
    """Policy gate should fail closed for generated or low-value candidates."""

    generated = policy_gate(
        MemoryIn(content="The assistant guessed a preference", source_type=SourceType.LLM_GENERATED),
        0.9,
    )
    low_value = policy_gate(MemoryIn(content="ok"), 0.2)

    assert generated.accept is False
    assert "llm_generated" in generated.reason
    assert low_value.accept is False
    assert "low long-term value" in low_value.reason


async def test_write_persists_and_indexes_accepted_memory() -> None:
    """Accepted memories should persist to PG first and then vector index."""

    services = Services()
    result = await write(
        MemoryIn(content="I prefer Python", user_id="u1", scope=Scope.USER),
        services,
    )

    assert result["accepted"] is True
    assert result["memory_id"] == "event-1"
    assert services.persisted[0][1] == "event"
    assert services.memory_store.indexed == [
        (
            ["event-1"],
            ["I prefer Python"],
            [{"memory_type": "event", "scope": "user", "workspace_id": "default"}],
        )
    ]


async def test_write_rejects_without_persisting_or_indexing() -> None:
    """Rejected memories should not touch persistence or vector index."""

    services = Services()
    result = await write(
        MemoryIn(content="assistant conclusion", source_type=SourceType.LLM_GENERATED),
        services,
    )

    assert result["accepted"] is False
    assert services.persisted == []
    assert services.memory_store.indexed == []
