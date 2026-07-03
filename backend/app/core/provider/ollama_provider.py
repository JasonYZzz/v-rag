"""Ollama provider implementations."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx


class OllamaEmbedding:
    """Ollama embedding provider."""

    def __init__(self, base_url: str, model: str, dim: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim = dim

    @property
    def dim(self) -> int:
        """Return embedding vector dimension."""

        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed text via Ollama's embed endpoint."""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": texts},
                timeout=60,
            )
            response.raise_for_status()
            embeddings = response.json()["embeddings"]
            return [_as_float_list(item) for item in embeddings]


class OllamaLLM:
    """Ollama streaming chat provider."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Collect the streaming response into one string."""

        return "".join([chunk async for chunk in self.stream(prompt, system=system)])

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        """Stream generated text from Ollama."""

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client, client.stream(
            "POST",
            f"{self._base_url}/api/chat",
            json={"model": self._model, "messages": messages, "stream": True},
            timeout=120,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                message = json.loads(line).get("message", {})
                content = message.get("content")
                if content:
                    yield str(content)


def _as_float_list(value: Any) -> list[float]:
    return [float(item) for item in value]
