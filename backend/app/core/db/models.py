"""SQLAlchemy metadata models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base."""


class Document(Base):
    """Uploaded document metadata."""

    __tablename__ = "document"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String, default="default")
    org_id: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    filename: Mapped[str] = mapped_column(String)
    source_path: Mapped[str] = mapped_column(Text)
    parser: Mapped[str] = mapped_column(String, default="pymupdf")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete")


class Chunk(Base):
    """Chunk metadata and text source of truth."""

    __tablename__ = "chunk"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(nullable=True)
    heading_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[Document] = relationship(back_populates="chunks")


class AgentGraphConfig(Base):
    """A named graph configuration with versioned publish state."""

    __tablename__ = "agent_graph_config"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String)
    workspace_id: Mapped[str] = mapped_column(String, default="default")
    current_published_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    versions: Mapped[list["AgentGraphVersion"]] = relationship(
        back_populates="config",
        cascade="all, delete",
        passive_deletes=True,
    )


class AgentGraphVersion(Base):
    """Versioned graph_config JSON."""

    __tablename__ = "agent_graph_version"
    __table_args__ = (UniqueConstraint("config_id", "version", name="uq_graph_config_version"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    config_id: Mapped[str] = mapped_column(
        ForeignKey("agent_graph_config.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer)
    graph: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    config: Mapped[AgentGraphConfig] = relationship(back_populates="versions")


class PublishHistory(Base):
    """Audit log for graph publish and rollback actions."""

    __tablename__ = "agent_graph_publish_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    config_id: Mapped[str] = mapped_column(
        ForeignKey("agent_graph_config.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RunTrace(Base):
    """Node-level trace for a routed graph run."""

    __tablename__ = "run_trace"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    graph_config_id: Mapped[str | None] = mapped_column(String, nullable=True)
    graph_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    query: Mapped[str] = mapped_column(Text)
    route_trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    node_io: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    intent: Mapped[str | None] = mapped_column(String, nullable=True)
    budget: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MemoryEvent(Base):
    """Episodic memory event stored in Postgres as source of truth."""

    __tablename__ = "memory_event"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    workspace_id: Mapped[str] = mapped_column(String, default="default")
    scope: Mapped[str] = mapped_column(String, default="user")
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String, default="active")
    sensitivity: Mapped[str] = mapped_column(String, default="normal")
    source_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str] = mapped_column(String, default="user")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ttl: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MemoryFact(Base):
    """Semantic memory fact represented as a graph-ready triple."""

    __tablename__ = "memory_fact"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    workspace_id: Mapped[str] = mapped_column(String, default="default")
    subject: Mapped[str] = mapped_column(String)
    predicate: Mapped[str] = mapped_column(String)
    object: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String, default="active")
    source_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MemoryProcedure(Base):
    """Procedural memory for skills and reusable workflows."""

    __tablename__ = "memory_procedure"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    workspace_id: Mapped[str] = mapped_column(String, default="default")
    skill_name: Mapped[str] = mapped_column(String)
    trigger: Mapped[str] = mapped_column(Text)
    action_spec: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MemoryFeedback(Base):
    """User correction or feedback for a memory record."""

    __tablename__ = "memory_feedback"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    memory_id: Mapped[str] = mapped_column(String)
    memory_type: Mapped[str] = mapped_column(String)
    feedback: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ConsolidationLog(Base):
    """Audit log for consolidation and forgetting operations."""

    __tablename__ = "memory_consolidation_log"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
