"""Deterministic local providers for development and browser smoke tests."""

from collections.abc import AsyncIterator


class MockEmbedding:
    """Tiny deterministic embedding provider."""

    def __init__(self, dim: int) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        """Return embedding dimension."""

        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts with a deterministic character hash."""

        return [_vector(text, self._dim) for text in texts]


class MockLLM:
    """Local streaming LLM for development."""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """Collect the stream into one string."""

        return "".join([token async for token in self.stream(prompt, system=system)])

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        """Yield a deterministic response."""

        _ = (prompt, system)
        for token in ["I ", "found ", "context ", "for ", "that."]:
            yield token


def _vector(text: str, dim: int) -> list[float]:
    vector = [0.0] * dim
    for char in text.lower():
        vector[ord(char) % dim] += 1.0
    return vector
