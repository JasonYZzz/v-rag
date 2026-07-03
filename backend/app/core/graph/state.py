"""LangGraph state object and intent taxonomy."""

from enum import StrEnum
from typing import Annotated, Any, NotRequired, TypedDict

from langgraph.graph.message import add_messages


class Intent(StrEnum):
    """Seven intent classes from spec section 6.2.1."""

    CHITCHAT = "chitchat"
    KNOWLEDGE_QA = "knowledge_qa"
    MULTIMODAL_DOC = "multimodal_doc"
    TOOL_ACTION = "tool_action"
    COMPLEX_TASK = "complex_task"
    CLARIFICATION = "clarification_needed"
    UNSUPPORTED = "unsupported_or_rejected"


class VragState(TypedDict, total=False):
    """State passed between graph nodes."""

    query: str
    user_id: NotRequired[str]
    session_id: NotRequired[str]
    workspace_id: NotRequired[str]
    knowledge_base_id: NotRequired[str]
    graph_config_id: NotRequired[str]
    graph_version: NotRequired[int]
    intent: NotRequired[Intent]
    confidence: NotRequired[float]
    route_trace: NotRequired[dict[str, Any]]
    memory_hits: NotRequired[list[dict[str, Any]]]
    retrieved_docs: NotRequired[list[dict[str, Any]]]
    context_blocks: NotRequired[list[dict[str, Any]]]
    generation: NotRequired[str]
    reflection: NotRequired[dict[str, Any] | None]
    errors: NotRequired[list[dict[str, Any]]]
    budget: NotRequired[dict[str, Any]]
    trace_id: NotRequired[str]
    node_io: NotRequired[list[dict[str, Any]]]
    messages: Annotated[list[Any], add_messages]
