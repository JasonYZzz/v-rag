"""Settings loading tests."""

import pytest

from app.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings should read provider and database values from environment."""

    monkeypatch.setenv("VRAG_LLM_PROVIDER", "openai")
    monkeypatch.setenv("VRAG_OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("VRAG_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/vrag")

    settings = Settings()

    assert settings.llm_provider == "openai"
    assert settings.openai_api_key.get_secret_value() == "sk-test"
    assert settings.vector_store == "inmemory"


def test_settings_defaults_are_safe() -> None:
    """Defaults should allow the app to start without external vector services."""

    settings = Settings()

    assert settings.vector_store == "inmemory"
    assert settings.embed_dim == 1536
