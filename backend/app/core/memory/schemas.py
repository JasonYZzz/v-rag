"""Memory service schemas."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Scope(StrEnum):
    """Memory visibility scope."""

    USER = "user"
    SESSION = "session"
    PROJECT = "project"
    WORKSPACE = "workspace"
    AGENT = "agent"
    ORG = "org"


class Status(StrEnum):
    """Memory lifecycle status."""

    ACTIVE = "active"
    CANDIDATE = "candidate"
    SUPERSEDED = "superseded"
    DELETED = "deleted"
    EXPIRED = "expired"


class Sensitivity(StrEnum):
    """Memory sensitivity classification."""

    NORMAL = "normal"
    PRIVATE = "private"
    SENSITIVE = "sensitive"


class SourceType(StrEnum):
    """Memory source provenance."""

    USER = "user"
    TOOL = "tool"
    DOCUMENT = "document"
    LLM_GENERATED = "llm_generated"


class MemoryType(StrEnum):
    """Memory storage type."""

    EVENT = "event"
    FACT = "fact"
    PROCEDURE = "procedure"


class MemoryIn(BaseModel):
    """Input candidate for long-term memory writing."""

    content: str
    user_id: str | None = None
    workspace_id: str = "default"
    scope: Scope = Scope.USER
    status: Status = Status.ACTIVE
    sensitivity: Sensitivity = Sensitivity.NORMAL
    source_type: SourceType = SourceType.USER
    source_event_id: str | None = None
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryOut(BaseModel):
    """Memory record returned by API and graph recall."""

    id: str
    memory_type: MemoryType
    content: str
    user_id: str | None = None
    workspace_id: str = "default"
    scope: Scope = Scope.USER
    status: Status = Status.ACTIVE
    sensitivity: Sensitivity = Sensitivity.NORMAL
    importance: float = 0.5
    source_type: SourceType = SourceType.USER


class MemoryFilter(BaseModel):
    """Memory list and forget filters."""

    memory_type: MemoryType | None = None
    user_id: str | None = None
    workspace_id: str = "default"
    scope: Scope | None = None
    status: Status | None = None
    ids: list[str] | None = None
    limit: int = Field(default=50, ge=1, le=200)


class MemoryPatch(BaseModel):
    """Mutable memory fields for the viewer/API."""

    status: Status | None = None
    sensitivity: Sensitivity | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    content: str | None = None


class MemoryFeedbackIn(BaseModel):
    """User feedback payload."""

    feedback: str

