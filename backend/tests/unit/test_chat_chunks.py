"""Chat SSE retrieved chunk event tests."""

from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app.core.retrieval.engine import RetrievedChunk
from app.deps import _globals
from app.main import app


class FakeRetrieval:
    """Retrieval engine returning one fixed hit."""

    async def search(
        self,
        query: str,
        top_k: int = 4,
        filter: dict[str, object] | None = None,
        text_lookup: dict[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        _ = (query, top_k, filter, text_lookup)
        return [
            RetrievedChunk(
                chunk_id="chunk-1",
                text="retrieved text",
                score=0.91,
                metadata={"page": 2, "doc": "doc-1"},
            )
        ]


class FakeLLM:
    """LLM returning one token."""

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        _ = (prompt, system)
        yield "Hi"

    async def complete(self, prompt: str, *, system: str = "") -> str:
        return "".join([token async for token in self.stream(prompt, system=system)])


def test_chat_emits_retrieved_event_before_tokens() -> None:
    """The first SSE frame should be the retrieved chunks event."""

    _globals["retrieval"] = FakeRetrieval()
    _globals["llm"] = FakeLLM()
    client = TestClient(app)

    response = client.post("/chat", json={"query": "hello", "top_k": 1})

    assert response.status_code == 200
    frames = response.text.strip().split("\n\n")
    assert frames[0].startswith("event: retrieved\n")
    assert '"chunk_id": "chunk-1"' in frames[0]
    assert '"text": "retrieved text"' in frames[0]
    assert '"score": 0.91' in frames[0]
    assert frames[1] == "data: Hi"
    assert frames[-1] == "data: [DONE]"
