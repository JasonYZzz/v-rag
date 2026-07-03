"""Read-only runtime configuration endpoint."""

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["config"])


@router.get("/config")
async def get_config() -> dict[str, object]:
    """Return non-sensitive runtime configuration for the admin console."""

    settings = get_settings()
    return {
        "llm_provider": settings.llm_provider,
        "embed_provider": settings.embed_provider,
        "openai_base_url": settings.openai_base_url,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_llm_model": settings.ollama_llm_model,
        "ollama_embed_model": settings.ollama_embed_model,
        "embed_dim": settings.embed_dim,
        "vector_store": settings.vector_store,
        "database_url": _mask_database_url(settings.database_url),
        "has_openai_key": settings.openai_api_key.get_secret_value() != "",
    }


def _mask_database_url(database_url: str) -> str:
    if "://" not in database_url or "@" not in database_url:
        return database_url
    scheme, rest = database_url.split("://", 1)
    credentials, host = rest.split("@", 1)
    if ":" not in credentials:
        return database_url
    user, _password = credentials.split(":", 1)
    return f"{scheme}://{user}:***@{host}"
