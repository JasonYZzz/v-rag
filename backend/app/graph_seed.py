"""Default graph seed."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.graph.config import GraphConfig
from app.core.graph.persistence import create_graph, get_published, publish_version

DEFAULT_GRAPH: dict[str, object] = {
    "version": 1,
    "entry": "classifier",
    "nodes": [
        {"id": "classifier", "type": "classifier"},
        {"id": "memory_recall", "type": "memory_recall"},
        {"id": "retrieve", "type": "retrieve"},
        {"id": "generate", "type": "generate"},
        {"id": "clarify", "type": "clarification"},
        {"id": "unsupported", "type": "unsupported"},
        {"id": "reflect", "type": "reflect"},
        {"id": "memory_write", "type": "memory_write"},
    ],
    "edges": [
        {"from": "classifier", "to": "memory_recall"},
        {"from": "memory_recall", "to": "retrieve", "condition": "intent=knowledge_qa"},
        {"from": "memory_recall", "to": "generate", "condition": "intent=chitchat"},
        {"from": "memory_recall", "to": "clarify", "condition": "intent=clarification_needed"},
        {"from": "memory_recall", "to": "unsupported", "condition": "intent=unsupported_or_rejected"},
        {"from": "memory_recall", "to": "unsupported", "condition": "intent=multimodal_doc"},
        {"from": "memory_recall", "to": "unsupported", "condition": "intent=tool_action"},
        {"from": "memory_recall", "to": "unsupported", "condition": "intent=complex_task"},
        {"from": "retrieve", "to": "generate"},
        {"from": "generate", "to": "reflect"},
        {"from": "clarify", "to": "reflect"},
        {"from": "unsupported", "to": "reflect"},
        {"from": "reflect", "to": "memory_write"},
    ],
    "exits": ["memory_write"],
}


async def ensure_default_graph(session: AsyncSession) -> None:
    """Seed and publish the default graph when no graph is published."""

    if await get_published(session) is not None:
        return
    _config, version = await create_graph(
        session,
        "Default routing graph",
        GraphConfig.model_validate(DEFAULT_GRAPH),
    )
    await publish_version(session, version.config_id, version.version)
