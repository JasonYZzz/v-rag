"""MemoryService tests."""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db.models import Base, MemoryFeedback
from app.core.memory.bm25 import BM25Index
from app.core.memory.schemas import (
    MemoryFeedbackIn,
    MemoryFilter,
    MemoryIn,
    MemoryPatch,
    MemoryType,
    Scope,
    Sensitivity,
    SourceType,
    Status,
)
from app.core.memory.service import MemoryService
from app.core.memory.store import MemoryVectorIndex
from app.core.storage.inmemory import InMemoryVectorStore


class FakeEmbedder:
    """Keyword fake embedder."""

    @property
    def dim(self) -> int:
        return 3

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [
            [
                1.0 if "python" in text.lower() else 0.0,
                1.0 if "spring" in text.lower() else 0.0,
                1.0 if "stack" in text.lower() else 0.0,
            ]
            for text in texts
        ]


async def _service() -> MemoryService:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return MemoryService(
        session_factory,
        MemoryVectorIndex(FakeEmbedder(), InMemoryVectorStore()),
        BM25Index(),
    )


async def test_memory_service_remember_recall_list_update_feedback_and_forget() -> None:
    """MemoryService should provide the public memory lifecycle API."""

    service = await _service()
    remembered = await service.remember(
        MemoryIn(content="I prefer Python", user_id="u1", scope=Scope.USER)
    )

    assert remembered["accepted"] is True
    recalled = await service.recall("python stack", user_id="u1", scope=Scope.USER)
    assert recalled["memories"][0]["content"] == "I prefer Python"
    assert "I prefer Python" in recalled["context"]

    listed = await service.list_memories(MemoryFilter(user_id="u1"))
    assert len(listed) == 1
    memory_id = listed[0].id
    updated = await service.update_memory(
        memory_id,
        MemoryPatch(sensitivity=Sensitivity.PRIVATE, importance=0.95),
    )
    assert updated.sensitivity is Sensitivity.PRIVATE
    assert updated.importance == 0.95

    await service.feedback(memory_id, MemoryType.EVENT, MemoryFeedbackIn(feedback="correct"))
    async with service.session_factory() as session:
        feedback = await session.get(MemoryFeedback, "feedback-1")
    assert feedback is not None
    assert feedback.feedback == "correct"

    deleted = await service.forget({"ids": [memory_id]})
    assert deleted == 1
    recalled_after_delete = await service.recall("python stack", user_id="u1", scope=Scope.USER)
    assert recalled_after_delete["memories"] == []


async def test_memory_service_writes_fact_records() -> None:
    """Structured triples should persist as semantic facts."""

    service = await _service()

    result = await service.remember(
        MemoryIn(
            content="team uses Spring",
            user_id="u1",
            scope=Scope.PROJECT,
            source_type=SourceType.DOCUMENT,
            subject="team",
            predicate="uses",
            object="Spring",
        )
    )

    assert result["memory_type"] == "fact"
    listed = await service.list_memories(MemoryFilter(memory_type=MemoryType.FACT, user_id="u1"))
    assert listed[0].content == "team uses Spring"
    assert listed[0].status is Status.ACTIVE
