"""Provider tests using mocked HTTP."""

import respx
from httpx import Response

from app.core.provider.factory import build_embedding_provider, build_llm_provider


@respx.mock
async def test_openai_embedding_calls_api() -> None:
    """OpenAI embedding should call /v1/embeddings and parse vectors."""

    respx.post("https://api.openai.com/v1/embeddings").mock(
        return_value=Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})
    )

    provider = build_embedding_provider("openai", api_key="sk-x", dim=2)
    vectors = await provider.embed(["hello"])

    assert vectors == [[0.1, 0.2]]


@respx.mock
async def test_openai_llm_stream_yields_chunks() -> None:
    """OpenAI streaming should yield delta text chunks."""

    sse = 'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\ndata: [DONE]\n\n'
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(200, text=sse)
    )

    llm = build_llm_provider("openai", api_key="sk-x")
    chunks = [chunk async for chunk in llm.stream("ping")]

    assert chunks == ["Hi"]


async def test_mock_provider_is_deterministic() -> None:
    """Mock providers should work without network access."""

    embedder = build_embedding_provider("mock", dim=4)
    llm = build_llm_provider("mock")

    assert await embedder.embed(["ab"]) == [[0.0, 1.0, 1.0, 0.0]]
    assert await llm.complete("hello") == "I found context for that."
