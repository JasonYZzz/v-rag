"""RAG chat endpoint with server-sent events."""

import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.schemas.chat import RetrievedChunkOut
from app.core.db.models import RunTrace
from app.core.db.session import get_session_factory
from app.core.graph.config import GraphConfig
from app.core.graph.persistence import get_published
from app.core.graph.runner import run
from app.core.graph.state import Intent, VragState
from app.deps import get_services
from app.graph_seed import ensure_default_graph

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request payload."""

    query: str
    top_k: int = 4
    graph_id: str | None = None


@router.post("")
async def chat(
    request: ChatRequest,
    services: Annotated[object, Depends(get_services)],
) -> StreamingResponse:
    """Execute the published routing graph and stream the generated answer as SSE."""

    trace_id = str(uuid.uuid4())
    async with get_session_factory()() as session:
        await ensure_default_graph(session)
        version = await get_published(session, request.graph_id)
        if version is None:
            raise RuntimeError("no published graph available")
        graph_config = GraphConfig.model_validate(version.graph)
        state = VragState(
            query=request.query,
            graph_config_id=version.config_id,
            graph_version=version.version,
            trace_id=trace_id,
            messages=[],
        )
        final_state = await run(graph_config, state, services)
        session.add(
            RunTrace(
                id=trace_id,
                graph_config_id=version.config_id,
                graph_version=version.version,
                query=request.query,
                route_trace=final_state.get("route_trace", {}),
                node_io=final_state.get("node_io", []),
                intent=_intent_value(final_state.get("intent")),
                budget=final_state.get("budget", {}),
            )
        )
        await session.commit()

    async def event_stream() -> AsyncIterator[bytes]:
        retrieved = [
            RetrievedChunkOut(
                chunk_id=str(doc.get("chunk_id", "")),
                text=str(doc.get("text", "")),
                score=float(doc.get("score", 0.0)),
                page=_optional_int(_metadata(doc).get("page")),
                document_id=_optional_str(_metadata(doc).get("doc")),
            ).model_dump()
            for doc in final_state.get("retrieved_docs", [])
        ]
        yield (
            "event: retrieved\n"
            f"data: {json.dumps(retrieved, ensure_ascii=False)}\n\n"
        ).encode()
        yield (
            "event: trace\n"
            f"data: {json.dumps({'trace_id': trace_id}, ensure_ascii=False)}\n\n"
        ).encode()
        generation = str(final_state.get("generation", ""))
        yield (
            "event: generation\n"
            f"data: {generation}\n\n"
        ).encode()
        for token in generation:
            yield f"data: {token}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _metadata(doc: dict[str, object]) -> dict[str, object]:
    metadata = doc.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _intent_value(value: object) -> str | None:
    if isinstance(value, Intent):
        return value.value
    return str(value) if value is not None else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None
