"""Read-only config endpoint tests."""

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.config import get_settings
from app.main import app


def test_config_endpoint_returns_non_secret_values(monkeypatch: MonkeyPatch) -> None:
    """Config endpoint should expose runtime values without leaking secrets."""

    monkeypatch.setenv("VRAG_OPENAI_API_KEY", "sk-secret")
    monkeypatch.setenv("VRAG_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/vrag")
    get_settings.cache_clear()
    client = TestClient(app)

    response = client.get("/config")

    assert response.status_code == 200
    body = response.json()
    assert body["llm_provider"] == "openai"
    assert body["embed_provider"] == "openai"
    assert body["vector_store"] == "inmemory"
    assert body["has_openai_key"] is True
    assert "sk-secret" not in response.text
    assert body["database_url"] == "postgresql+asyncpg://u:***@localhost/vrag"
    get_settings.cache_clear()
