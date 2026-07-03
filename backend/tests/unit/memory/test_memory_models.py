"""Memory model and schema tests."""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db.models import (
    Base,
    ConsolidationLog,
    MemoryEvent,
    MemoryFact,
    MemoryFeedback,
    MemoryProcedure,
)
from app.core.memory.schemas import MemoryIn, Scope, Sensitivity, SourceType, Status


async def test_memory_models_persist_event_fact_procedure_feedback_and_logs() -> None:
    """Memory tables should persist the P3 source-of-truth records."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        event = MemoryEvent(id="event-1", content="User prefers Python", user_id="u1")
        fact = MemoryFact(
            id="fact-1",
            user_id="u1",
            subject="user",
            predicate="prefers_language",
            object="Python",
            source_event_id=event.id,
        )
        procedure = MemoryProcedure(
            id="procedure-1",
            user_id="u1",
            skill_name="deploy",
            trigger="when release is requested",
            action_spec="run checks then publish",
        )
        feedback = MemoryFeedback(
            id="feedback-1",
            memory_id=event.id,
            memory_type="event",
            feedback="keep",
        )
        log = ConsolidationLog(id="log-1", user_id="u1", action="merge", details={"merged": 1})
        session.add_all([event, fact, procedure, feedback, log])
        await session.commit()

    async with session_factory() as session:
        stored_event = await session.get(MemoryEvent, event.id)
        stored_fact = await session.get(MemoryFact, fact.id)
        stored_procedure = await session.get(MemoryProcedure, procedure.id)
        stored_feedback = await session.get(MemoryFeedback, feedback.id)
        stored_log = await session.get(ConsolidationLog, log.id)

    assert stored_event is not None
    assert stored_event.workspace_id == "default"
    assert stored_event.scope == "user"
    assert stored_event.status == "active"
    assert stored_fact is not None
    assert (stored_fact.subject, stored_fact.predicate, stored_fact.object) == (
        "user",
        "prefers_language",
        "Python",
    )
    assert stored_procedure is not None
    assert stored_procedure.version == 1
    assert stored_feedback is not None
    assert stored_feedback.memory_id == event.id
    assert stored_log is not None
    assert stored_log.details == {"merged": 1}


def test_memory_in_schema_defaults_and_enums() -> None:
    """MemoryIn should expose controlled enum defaults for write policy."""

    memory = MemoryIn(content="I prefer Python", user_id="u1")

    assert memory.scope is Scope.USER
    assert memory.status is Status.ACTIVE
    assert memory.sensitivity is Sensitivity.NORMAL
    assert memory.source_type is SourceType.USER
    assert memory.workspace_id == "default"
