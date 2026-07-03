"""Provider factories."""

from app.config import Settings
from app.core.provider.base import EmbeddingProvider, LLMProvider
from app.core.provider.ollama_provider import OllamaEmbedding, OllamaLLM
from app.core.provider.openai_provider import OpenAIEmbedding, OpenAILLM

_OPENAI_LLM_MODEL = "gpt-4o-mini"
_OPENAI_EMBED_MODEL = "text-embedding-3-small"


def build_llm_provider(
    kind: str,
    *,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> LLMProvider:
    """Create an LLM provider by kind."""

    if kind == "openai":
        return OpenAILLM(api_key, base_url or "https://api.openai.com/v1", model or _OPENAI_LLM_MODEL)
    if kind == "ollama":
        return OllamaLLM(base_url or "http://localhost:11434", model or "qwen2.5:7b")
    raise ValueError(f"unknown llm provider: {kind}")


def build_embedding_provider(
    kind: str,
    *,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    dim: int = 1536,
) -> EmbeddingProvider:
    """Create an embedding provider by kind."""

    if kind == "openai":
        return OpenAIEmbedding(api_key, base_url or "https://api.openai.com/v1", model or _OPENAI_EMBED_MODEL, dim)
    if kind == "ollama":
        return OllamaEmbedding(base_url or "http://localhost:11434", model or "nomic-embed-text", dim)
    raise ValueError(f"unknown embedding provider: {kind}")


def llm_from_settings(settings: Settings) -> LLMProvider:
    """Build an LLM provider from settings."""

    return build_llm_provider(
        settings.llm_provider,
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=(
            settings.openai_base_url
            if settings.llm_provider == "openai"
            else settings.ollama_base_url
        ),
        model=settings.ollama_llm_model if settings.llm_provider == "ollama" else "",
    )


def embedder_from_settings(settings: Settings) -> EmbeddingProvider:
    """Build an embedding provider from settings."""

    return build_embedding_provider(
        settings.embed_provider,
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=(
            settings.openai_base_url
            if settings.embed_provider == "openai"
            else settings.ollama_base_url
        ),
        model=settings.ollama_embed_model if settings.embed_provider == "ollama" else "",
        dim=settings.embed_dim,
    )
