"""Model provider protocols."""

from collections.abc import AsyncIterator
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Embedding model protocol."""

    @property
    def dim(self) -> int:
        """Return embedding vector dimension."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""


class LLMProvider(Protocol):
    """Generation model protocol."""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Return a complete response for a prompt."""

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        """Yield generated text chunks."""
        if False:
            yield ""
