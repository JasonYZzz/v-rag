"""Vector store factory."""

from app.core.storage.base import VectorStore
from app.core.storage.inmemory import InMemoryVectorStore
from app.core.storage.zvec_store import ZvecVectorStore


def build_vector_store(kind: str, **kwargs: object) -> VectorStore:
    """Create a vector store by kind."""

    if kind == "inmemory":
        return InMemoryVectorStore()
    if kind == "zvec":
        raw_dim = kwargs.get("dim", 1536)
        return ZvecVectorStore(
            path=str(kwargs.get("path", "./data/zvec")),
            dim=raw_dim if isinstance(raw_dim, int) else int(str(raw_dim)),
        )
    raise ValueError(f"unknown vector store: {kind}")
