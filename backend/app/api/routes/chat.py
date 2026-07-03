"""RAG chat endpoint with server-sent events."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.provider.base import LLMProvider
from app.core.retrieval.engine import RetrievalEngine
from app.deps import get_llm, get_retrieval

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request payload."""

    query: str
    top_k: int = 4


def _build_prompt(query: str, contexts: list[str]) -> str:
    joined = "\n---\n".join(contexts)
    return f"Use the following context to answer. If it is insufficient, say so.\n\nContext:\n{joined}\n\nQuestion: {query}"


@router.post("")
async def chat(
    request: ChatRequest,
    llm: Annotated[LLMProvider, Depends(get_llm)],
    retrieval: Annotated[RetrievalEngine, Depends(get_retrieval)],
) -> StreamingResponse:
    """Retrieve context and stream the generated answer as SSE."""

    hits = await retrieval.search(request.query, top_k=request.top_k)
    prompt = _build_prompt(request.query, [hit.text for hit in hits])

    async def event_stream() -> AsyncIterator[bytes]:
        async for token in llm.stream(prompt, system="You are the v-rag assistant."):
            yield f"data: {token}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
