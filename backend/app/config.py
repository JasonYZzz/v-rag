"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """v-rag backend settings."""

    model_config = SettingsConfigDict(env_prefix="VRAG_", env_file=".env")

    llm_provider: str = "openai"
    embed_provider: str = "openai"
    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen2.5:7b"
    ollama_embed_model: str = "nomic-embed-text"

    embed_dim: int = 1536

    vector_store: str = "inmemory"
    zvec_path: str = "./data/zvec"
    database_url: str = "postgresql+asyncpg://vrag:vrag@localhost:5432/vrag"

    langfuse_public_key: SecretStr = SecretStr("")
    langfuse_secret_key: SecretStr = SecretStr("")
    langfuse_host: str = "https://cloud.langfuse.com"
    otel_exporter_otlp_endpoint: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for dependency injection."""

    return Settings()
