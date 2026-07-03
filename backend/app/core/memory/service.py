"""Public MemoryService API."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.models import (
    ConsolidationLog,
    MemoryEvent,
    MemoryFact,
    MemoryFeedback,
    MemoryProcedure,
)
from app.core.memory import consolidation, reader, writer
from app.core.memory.bm25 import BM25Index
from app.core.memory.graph_adapter import GraphAdapter, NoopGraphAdapter
from app.core.memory.schemas import (
    MemoryFeedbackIn,
    MemoryFilter,
    MemoryIn,
    MemoryOut,
    MemoryPatch,
    MemoryType,
    Scope,
    Sensitivity,
    SourceType,
    Status,
)
from app.core.memory.store import MemoryVectorIndex


class MemoryService:
    """Long-term memory facade used by graph nodes and APIs."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        memory_store: MemoryVectorIndex,
        bm25: BM25Index,
        graph_adapter: GraphAdapter | None = None,
        session_factory_provider: Callable[[], async_sessionmaker[AsyncSession]] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._session_factory_provider = session_factory_provider
        self.memory_store = memory_store
        self.bm25 = bm25
        self.graph_adapter = graph_adapter or NoopGraphAdapter()

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the current session factory."""

        return self._session_factory_provider() if self._session_factory_provider else self._session_factory

    async def remember(self, input_: MemoryIn) -> dict[str, Any]:
        """Write a memory through the Policy Gate."""

        return await writer.write(input_, self)

    async def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        scope: Scope | str | None = None,
        workspace_id: str = "default",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Recall relevant memories through the Memory Gate."""

        scope_value = scope.value if isinstance(scope, Scope) else scope
        return await reader.recall(
            query,
            self,
            top_k=top_k,
            scope=scope_value,
            workspace_id=workspace_id,
            user_id=user_id,
        )

    async def consolidate(self, user_id: str | None, workspace_id: str) -> dict[str, int]:
        """Run consolidation."""

        return await consolidation.consolidate(user_id, workspace_id, self)

    async def forget(self, filter_: dict[str, Any]) -> int:
        """Soft-delete memories and remove vector indexes."""

        return await consolidation.forget(filter_, self)

    async def list_memories(self, filter_: MemoryFilter) -> list[MemoryOut]:
        """List memory records."""

        async with self.session_factory() as session:
            events = await self._list_events(session, filter_)
            facts = await self._list_facts(session, filter_)
            procedures = await self._list_procedures(session, filter_)
        return [*events, *facts, *procedures][: filter_.limit]

    async def update_memory(self, memory_id: str, patch: MemoryPatch) -> MemoryOut:
        """Update a memory event/fact/procedure."""

        async with self.session_factory() as session:
            event = await session.get(MemoryEvent, memory_id)
            if event is not None:
                if patch.status is not None:
                    event.status = patch.status.value
                if patch.sensitivity is not None:
                    event.sensitivity = patch.sensitivity.value
                if patch.importance is not None:
                    event.importance = patch.importance
                if patch.content is not None:
                    event.content = patch.content
                await session.commit()
                return _event_out(event)
            fact = await session.get(MemoryFact, memory_id)
            if fact is not None:
                if patch.status is not None:
                    fact.status = patch.status.value
                await session.commit()
                return _fact_out(fact)
            procedure = await session.get(MemoryProcedure, memory_id)
            if procedure is not None:
                if patch.status is not None:
                    procedure.status = patch.status.value
                await session.commit()
                return _procedure_out(procedure)
        raise KeyError(f"memory not found: {memory_id}")

    async def feedback(
        self, memory_id: str, memory_type: MemoryType, fb: MemoryFeedbackIn
    ) -> None:
        """Persist user feedback for a memory."""

        async with self.session_factory() as session:
            feedback_id = f"feedback-{len((await session.scalars(select(MemoryFeedback))).all()) + 1}"
            session.add(
                MemoryFeedback(
                    id=feedback_id,
                    memory_id=memory_id,
                    memory_type=memory_type.value,
                    feedback=fb.feedback,
                )
            )
            await session.commit()

    async def memory_persist(
        self, input_: MemoryIn, memory_type: str, importance: float
    ) -> str:
        """Persist a writer-accepted memory and update lexical/graph indexes."""

        async with self.session_factory() as session:
            if memory_type == MemoryType.FACT.value:
                fact = MemoryFact(
                    user_id=input_.user_id,
                    workspace_id=input_.workspace_id,
                    subject=input_.subject or "",
                    predicate=input_.predicate or "",
                    object=input_.object or "",
                    confidence=input_.confidence,
                    status=input_.status.value,
                    source_event_id=input_.source_event_id,
                )
                session.add(fact)
                await session.commit()
                await session.refresh(fact)
                await self.graph_adapter.upsert_fact(
                    {
                        "id": fact.id,
                        "subject": fact.subject,
                        "predicate": fact.predicate,
                        "object": fact.object,
                    }
                )
                self.bm25.add([fact.id], [input_.content])
                return fact.id
            event = MemoryEvent(
                user_id=input_.user_id,
                workspace_id=input_.workspace_id,
                scope=input_.scope.value,
                content=input_.content,
                importance=importance,
                status=input_.status.value,
                sensitivity=input_.sensitivity.value,
                source_event_id=input_.source_event_id,
                source_type=input_.source_type.value,
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            self.bm25.add([event.id], [event.content])
            return event.id

    async def memory_lookup(self, ids: list[str]) -> list[dict[str, Any]]:
        """Lookup memories by id for reader merge."""

        if not ids:
            return []
        async with self.session_factory() as session:
            events = (
                await session.scalars(select(MemoryEvent).where(MemoryEvent.id.in_(ids)))
            ).all()
            facts = (await session.scalars(select(MemoryFact).where(MemoryFact.id.in_(ids)))).all()
        return [*(_event_dict(event) for event in events), *(_fact_dict(fact) for fact in facts)]

    async def memory_recent_episodic(
        self, user_id: str | None, workspace_id: str, limit: int
    ) -> list[dict[str, Any]]:
        """Return recent active episodic memories."""

        async with self.session_factory() as session:
            stmt = (
                select(MemoryEvent)
                .where(MemoryEvent.workspace_id == workspace_id)
                .where(MemoryEvent.status == Status.ACTIVE.value)
                .order_by(MemoryEvent.created_at.desc())
                .limit(limit)
            )
            if user_id is not None:
                stmt = stmt.where(MemoryEvent.user_id == user_id)
            events = (await session.scalars(stmt)).all()
        return [{**_event_dict(event), "_score": float(event.importance)} for event in events]

    async def merge_similar_facts(self, user_id: str | None, workspace_id: str) -> int:
        """Supersede duplicate subject/predicate facts, keeping the newest."""

        async with self.session_factory() as session:
            stmt = (
                select(MemoryFact)
                .where(MemoryFact.workspace_id == workspace_id)
                .where(MemoryFact.status == Status.ACTIVE.value)
                .order_by(MemoryFact.created_at.desc())
            )
            if user_id is not None:
                stmt = stmt.where(MemoryFact.user_id == user_id)
            facts = list((await session.scalars(stmt)).all())
            seen: set[tuple[str, str]] = set()
            merged = 0
            for fact in facts:
                key = (fact.subject, fact.predicate)
                if key in seen:
                    fact.status = Status.SUPERSEDED.value
                    merged += 1
                else:
                    seen.add(key)
            await session.commit()
            return merged

    async def expire_overdue(self, user_id: str | None, workspace_id: str) -> int:
        """Mark overdue events and facts as expired."""

        now = datetime.utcnow()
        async with self.session_factory() as session:
            event_stmt = (
                update(MemoryEvent)
                .where(MemoryEvent.workspace_id == workspace_id)
                .where(MemoryEvent.valid_to.is_not(None))
                .where(MemoryEvent.valid_to < now)
                .values(status=Status.EXPIRED.value)
            )
            fact_stmt = (
                update(MemoryFact)
                .where(MemoryFact.workspace_id == workspace_id)
                .where(MemoryFact.valid_to.is_not(None))
                .where(MemoryFact.valid_to < now)
                .values(status=Status.EXPIRED.value)
            )
            if user_id is not None:
                event_stmt = event_stmt.where(MemoryEvent.user_id == user_id)
                fact_stmt = fact_stmt.where(MemoryFact.user_id == user_id)
            event_result = await session.execute(event_stmt)
            fact_result = await session.execute(fact_stmt)
            await session.commit()
        return _rowcount(event_result) + _rowcount(fact_result)

    async def log_consolidation(self, user_id: str | None, details: dict[str, object]) -> None:
        """Write consolidation audit log."""

        async with self.session_factory() as session:
            session.add(ConsolidationLog(user_id=user_id, action="consolidate", details=details))
            await session.commit()

    async def mark_deleted(self, filter_: dict[str, Any]) -> int:
        """Soft-delete selected memories."""

        ids = [str(id_) for id_ in filter_.get("ids", [])]
        if not ids:
            return 0
        async with self.session_factory() as session:
            event_result = await session.execute(
                update(MemoryEvent).where(MemoryEvent.id.in_(ids)).values(status=Status.DELETED.value)
            )
            fact_result = await session.execute(
                update(MemoryFact).where(MemoryFact.id.in_(ids)).values(status=Status.DELETED.value)
            )
            procedure_result = await session.execute(
                update(MemoryProcedure)
                .where(MemoryProcedure.id.in_(ids))
                .values(status=Status.DELETED.value)
            )
            await session.commit()
        return int(
            _rowcount(event_result)
            + _rowcount(fact_result)
            + _rowcount(procedure_result)
        )

    async def _list_events(
        self, session: AsyncSession, filter_: MemoryFilter
    ) -> list[MemoryOut]:
        if filter_.memory_type not in (None, MemoryType.EVENT):
            return []
        stmt = select(MemoryEvent).where(MemoryEvent.workspace_id == filter_.workspace_id)
        stmt = _apply_common_filters(stmt, MemoryEvent, filter_)
        rows = (await session.scalars(stmt.limit(filter_.limit))).all()
        return [_event_out(row) for row in rows]

    async def _list_facts(self, session: AsyncSession, filter_: MemoryFilter) -> list[MemoryOut]:
        if filter_.memory_type not in (None, MemoryType.FACT):
            return []
        stmt = select(MemoryFact).where(MemoryFact.workspace_id == filter_.workspace_id)
        stmt = _apply_common_filters(stmt, MemoryFact, filter_)
        rows = (await session.scalars(stmt.limit(filter_.limit))).all()
        return [_fact_out(row) for row in rows]

    async def _list_procedures(
        self, session: AsyncSession, filter_: MemoryFilter
    ) -> list[MemoryOut]:
        if filter_.memory_type not in (None, MemoryType.PROCEDURE):
            return []
        stmt = select(MemoryProcedure).where(MemoryProcedure.workspace_id == filter_.workspace_id)
        stmt = _apply_common_filters(stmt, MemoryProcedure, filter_)
        rows = (await session.scalars(stmt.limit(filter_.limit))).all()
        return [_procedure_out(row) for row in rows]


def _apply_common_filters(stmt: Any, model: Any, filter_: MemoryFilter) -> Any:
    if filter_.user_id is not None and hasattr(model, "user_id"):
        stmt = stmt.where(model.user_id == filter_.user_id)
    if filter_.status is not None:
        stmt = stmt.where(model.status == filter_.status.value)
    if filter_.ids:
        stmt = stmt.where(model.id.in_(filter_.ids))
    return stmt


def _rowcount(result: Any) -> int:
    return int(getattr(result, "rowcount", 0) or 0)


def _event_out(event: MemoryEvent) -> MemoryOut:
    return MemoryOut(
        id=event.id,
        memory_type=MemoryType.EVENT,
        content=event.content,
        user_id=event.user_id,
        workspace_id=event.workspace_id,
        scope=Scope(event.scope),
        status=Status(event.status),
        sensitivity=Sensitivity(event.sensitivity),
        importance=event.importance,
        source_type=SourceType(event.source_type),
    )


def _fact_out(fact: MemoryFact) -> MemoryOut:
    return MemoryOut(
        id=fact.id,
        memory_type=MemoryType.FACT,
        content=f"{fact.subject} {fact.predicate} {fact.object}",
        user_id=fact.user_id,
        workspace_id=fact.workspace_id,
        scope=Scope.PROJECT,
        status=Status(fact.status),
        sensitivity=Sensitivity.NORMAL,
        importance=fact.confidence,
        source_type=SourceType.DOCUMENT,
    )


def _procedure_out(procedure: MemoryProcedure) -> MemoryOut:
    return MemoryOut(
        id=procedure.id,
        memory_type=MemoryType.PROCEDURE,
        content=f"{procedure.trigger}\n{procedure.action_spec}",
        user_id=procedure.user_id,
        workspace_id=procedure.workspace_id,
        scope=Scope.USER,
        status=Status(procedure.status),
        sensitivity=Sensitivity.NORMAL,
        importance=0.5,
        source_type=SourceType.USER,
    )


def _event_dict(event: MemoryEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "content": event.content,
        "memory_type": "event",
        "scope": event.scope,
        "status": event.status,
        "sensitivity": event.sensitivity,
        "workspace_id": event.workspace_id,
        "user_id": event.user_id,
        "importance": event.importance,
        "created_at": event.created_at.isoformat() if event.created_at else "",
    }


def _fact_dict(fact: MemoryFact) -> dict[str, Any]:
    return {
        "id": fact.id,
        "content": f"{fact.subject} {fact.predicate} {fact.object}",
        "memory_type": "fact",
        "subject": fact.subject,
        "predicate": fact.predicate,
        "object": fact.object,
        "scope": "project",
        "status": fact.status,
        "workspace_id": fact.workspace_id,
        "user_id": fact.user_id,
        "importance": fact.confidence,
        "created_at": fact.created_at.isoformat() if fact.created_at else "",
    }
