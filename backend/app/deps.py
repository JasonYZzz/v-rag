"""Application dependency container."""

from app.config import Settings, get_settings
from app.core.db.session import get_session_factory, init_engine
from app.core.memory.bm25 import BM25Index
from app.core.memory.service import MemoryService
from app.core.memory.store import MemoryVectorIndex
from app.core.provider.base import EmbeddingProvider, LLMProvider
from app.core.provider.factory import embedder_from_settings, llm_from_settings
from app.core.retrieval.engine import RetrievalEngine
from app.core.storage.base import VectorStore
from app.core.storage.factory import build_vector_store
from app.core.tools.builtin import register_builtin_tools
from app.core.tools.registry import tool_registry

_globals: dict[str, object] = {}


def init_deps(settings: Settings | None = None) -> None:
    """Initialize process-wide dependencies for API routes."""

    loaded_settings = settings or get_settings()
    init_engine(loaded_settings.database_url)
    embedder = embedder_from_settings(loaded_settings)
    store = build_vector_store(
        loaded_settings.vector_store,
        path=loaded_settings.zvec_path,
        dim=loaded_settings.embed_dim,
    )
    register_builtin_tools(tool_registry)
    retrieval = RetrievalEngine(embedder, store)
    memory = MemoryService(
        get_session_factory(),
        MemoryVectorIndex(_DynamicEmbedder(), store),
        BM25Index(),
        session_factory_provider=get_session_factory,
    )
    _globals.clear()
    _globals.update(
        settings=loaded_settings,
        embedder=embedder,
        llm=llm_from_settings(loaded_settings),
        store=store,
        retrieval=retrieval,
        tools=tool_registry,
        memory=memory,
    )


def get_retrieval() -> RetrievalEngine:
    """Return the singleton retrieval engine."""

    return _globals["retrieval"]  # type: ignore[return-value]


def get_llm() -> LLMProvider:
    """Return the singleton LLM provider."""

    return _globals["llm"]  # type: ignore[return-value]


def get_embedder() -> EmbeddingProvider:
    """Return the singleton embedding provider."""

    return _globals["embedder"]  # type: ignore[return-value]


def get_services() -> object:
    """Return the graph service container."""

    return type(
        "GraphServices",
        (),
        {
            "embedder": _globals["embedder"],
            "llm": _globals["llm"],
            "retrieval": _globals["retrieval"],
            "tools": _globals["tools"],
            "memory": _globals["memory"],
        },
    )()


def get_memory() -> MemoryService:
    """Return the singleton MemoryService."""

    return _globals["memory"]  # type: ignore[return-value]


def get_vector_store() -> VectorStore:
    """Return the singleton vector store."""

    return _globals["store"]  # type: ignore[return-value]


class _DynamicEmbedder:
    """Embedder proxy that follows test/runtime dependency overrides."""

    @property
    def dim(self) -> int:
        return get_embedder().dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await get_embedder().embed(texts)
