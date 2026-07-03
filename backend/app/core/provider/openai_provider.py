"""OpenAI-compatible provider implementations."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx


class OpenAIEmbedding:
    """OpenAI-compatible embedding provider."""

    def __init__(self, api_key: str, base_url: str, model: str, dim: int) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim = dim

    @property
    def dim(self) -> int:
        """Return embedding vector dimension."""

        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed text via the OpenAI-compatible embeddings endpoint."""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"input": texts, "model": self._model},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()["data"]
            return [_as_float_list(item["embedding"]) for item in data]


class OpenAILLM:
    """OpenAI-compatible streaming chat provider."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Collect the streaming response into one string."""

        return "".join([chunk async for chunk in self.stream(prompt, system=system)])

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        """Stream text deltas from the chat completions endpoint."""

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client, client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "messages": messages, "stream": True},
            timeout=120,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line.removeprefix("data: ").strip()
                if payload == "[DONE]":
                    continue
                delta = json.loads(payload)["choices"][0]["delta"].get("content")
                if delta:
                    yield str(delta)


def _as_float_list(value: Any) -> list[float]:
    return [float(item) for item in value]
