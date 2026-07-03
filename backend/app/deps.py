"""Application dependency container."""

from app.config import Settings, get_settings
from app.core.db.session import init_engine
from app.core.provider.base import EmbeddingProvider, LLMProvider
from app.core.provider.factory import embedder_from_settings, llm_from_settings
from app.core.retrieval.engine import RetrievalEngine
from app.core.storage.base import VectorStore
from app.core.storage.factory import build_vector_store

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
    retrieval = RetrievalEngine(embedder, store)
    _globals.clear()
    _globals.update(
        settings=loaded_settings,
        embedder=embedder,
        llm=llm_from_settings(loaded_settings),
        store=store,
        retrieval=retrieval,
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
        },
    )()


def get_vector_store() -> VectorStore:
    """Return the singleton vector store."""

    return _globals["store"]  # type: ignore[return-value]
