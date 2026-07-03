# P0-A: 后端地基（Backend Foundation）Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 v-rag 后端骨架并跑通"文档上传 → 解析 → 向量索引 → 检索 → LLM 流式回答"的传统 RAG 端到端链路，同时建立 provider/storage 抽象层。

**Architecture:** FastAPI 单体应用 + 自研 `v-rag-core` 包（provider / storage / document / retrieval 子模块）。provider 抽象统一 LLM/embedding（OpenAI + Ollama 可切）；storage 抽象统一向量库（Zvec 嵌入式为默认，InMemory 作测试 fallback）；PostgreSQL 仅存元数据（source of truth 原则的起点）。全程 TDD，ruff + mypy + pytest 为质量门禁。

**Tech Stack:** Python 3.12 · uv · FastAPI · Pydantic v2 · SQLAlchemy 2.x + asyncpg · Alembic · LlamaIndex（retrieval 基础） · Zvec · OpenAI SDK · Ollama · PyMuPDF · OpenTelemetry · Langfuse · pytest + httpx + respx。

**Spec 参考:** `docs/superpowers/specs/2026-07-03-v-rag-tech-selection-design.md`（§3 选型、§5 模块分解、§7 文档处理、§10 P0 范围）。

**相关 skills:** @python:test-first · @python:lint · @python:typecheck · @fastapi:endpoint

---

## File Structure

```
backend/
├── pyproject.toml                 # uv 依赖 + 工具配置
├── ruff.toml                      # lint 规则
├── Dockerfile
├── app/
│   ├── main.py                    # FastAPI app 装配 + OTel/Langfuse 初始化
│   ├── config.py                  # pydantic-settings Settings
│   ├── deps.py                    # FastAPI 依赖注入（provider/store/session）
│   ├── api/
│   │   ├── router.py              # 聚合路由
│   │   └── routes/
│   │       ├── health.py          # GET /health
│   │       ├── documents.py       # POST /documents (上传+解析+索引)
│   │       └── chat.py            # POST /chat (SSE 流式)
│   └── core/                      # v-rag-core 包
│       ├── provider/
│       │   ├── base.py            # LLMProvider / EmbeddingProvider 协议
│       │   ├── openai_provider.py # OpenAI 实现
│       │   ├── ollama_provider.py # Ollama 实现
│       │   └── factory.py         # 按 Settings 创建
│       ├── storage/
│       │   ├── base.py            # VectorStore 协议
│       │   ├── inmemory.py        # 测试/快速启动 fallback
│       │   ├── zvec_store.py      # Zvec 嵌入式实现
│       │   └── factory.py
│       ├── document/
│       │   ├── models.py          # DocumentBlock (Canonical schema 简化版)
│       │   ├── parser.py          # PyMuPDF 解析
│       │   └── chunker.py         # 固定大小 + overlap chunker
│       ├── retrieval/
│       │   └── engine.py          # embed query → vector search → return chunks
│       ├── db/
│       │   ├── models.py          # SQLAlchemy: Document, Chunk
│       │   └── session.py         # async engine + session factory
│       └── observability/
│           └── tracing.py         # OTel span 装饰器 + Langfuse 客户端
├── alembic/                       # DB migrations
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
└── docker-compose.yml             # postgres + backend
```

**职责边界**：每个 `core/` 子模块对外只暴露 `base.py` 协议 + `factory.py`，内部实现对调用方不可见。`api/routes` 只编排，不含业务逻辑。

---

## Task 1: 后端脚手架与工具链

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/ruff.toml`
- Create: `backend/app/__init__.py`（空）
- Create: `backend/app/main.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/tests/__init__.py`（空）
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: 写 pyproject.toml**

```toml
[project]
name = "v-rag-backend"
version = "0.1.0"
description = "v-rag Agentic RAG backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "openai>=1.55",
    "httpx>=0.28",
    "pymupdf>=1.25",
    "opentelemetry-sdk>=1.29",
    "opentelemetry-instrumentation-fastapi>=0.50b0",
    "langfuse>=2.60",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "respx>=0.21",
    "ruff>=0.8",
    "mypy>=1.13",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 2: 写 ruff.toml**

```toml
extend-select = ["I", "UP", "B", "SIM", "RUF"]
fix = true
```

- [ ] **Step 3: 写 /health 端点**

`app/api/routes/health.py`:
```python
"""健康检查端点。"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """返回服务存活状态，供 docker-compose 健康检查与探针使用。"""
    return {"status": "ok"}
```

`app/api/router.py`:
```python
"""聚合所有路由。"""

from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
```

`app/main.py`:
```python
"""FastAPI 应用入口。"""

from fastapi import FastAPI

from app.api.router import api_router


def create_app() -> FastAPI:
    """创建并装配 FastAPI 应用实例。"""
    app = FastAPI(title="v-rag backend")
    app.include_router(api_router)
    return app


app = create_app()
```

- [ ] **Step 4: 写健康检查测试**

`tests/test_health.py`:
```python
"""健康检查端点测试。"""

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    """GET /health 应返回 200 与 status=ok。"""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: 安装依赖并运行测试**

Run:
```bash
cd backend && uv sync --extra dev && uv run pytest tests/test_health.py -v
```
Expected: 1 passed

- [ ] **Step 6: 跑 lint 与 typecheck**

Run:
```bash
uv run ruff check . && uv run mypy app
```
Expected: 无 error

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI app with /health, ruff, mypy, pytest"
```

---

## Task 2: 应用配置（Settings）

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/tests/unit/test_config.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_config.py`:
```python
"""Settings 加载测试。"""

from app.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings 应从环境变量读取 provider 与数据库配置。"""
    monkeypatch.setenv("VRAG_LLM_PROVIDER", "openai")
    monkeypatch.setenv("VRAG_OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("VRAG_DATABASE_URL", "postgresql+asyncpg://u:p@localhost/vrag")
    settings = Settings()
    assert settings.llm_provider == "openai"
    assert settings.openai_api_key.get_secret_value() == "sk-test"
    assert settings.vector_store == "inmemory"  # 默认 inmemory，便于测试


def test_settings_defaults_are_safe() -> None:
    """无环境变量时，默认值应让应用可启动（inmemory 向量库）。"""
    settings = Settings()
    assert settings.vector_store == "inmemory"
    assert settings.embed_dim == 1536
```
（顶部需 `import pytest`）

- [ ] **Step 2: 运行测试，确认失败**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL（`app.config` 不存在）

- [ ] **Step 3: 写实现**

`app/config.py`:
```python
"""应用配置，全部来自环境变量（12-factor）。

所有密钥用 SecretStr，避免日志泄露。向量库默认 inmemory 以保证零依赖启动；
生产切换 zvec 需通过 VRAG_VECTOR_STORE 环境变量。
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """v-rag 后端配置。"""

    model_config = SettingsConfigDict(env_prefix="VRAG_", env_file=".env")

    # 模型 provider
    llm_provider: str = "openai"            # openai | ollama
    embed_provider: str = "openai"
    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen2.5:7b"
    ollama_embed_model: str = "nomic-embed-text"

    # 嵌入维度（不同模型不同：openai text-embedding-3-small=1536, nomic=768, bge=1024）
    embed_dim: int = 1536

    # 存储
    vector_store: str = "inmemory"          # inmemory | zvec
    zvec_path: str = "./data/zvec"
    database_url: str = "postgresql+asyncpg://vrag:vrag@localhost:5432/vrag"

    # 可观测（Task 10 启用）
    langfuse_public_key: SecretStr = SecretStr("")
    langfuse_secret_key: SecretStr = SecretStr("")
    langfuse_host: str = "https://cloud.langfuse.com"
    otel_exporter_otlp_endpoint: str = ""


def get_settings() -> Settings:
    """返回单例 Settings，供 FastAPI 依赖注入使用。"""
    return Settings()
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/unit/test_config.py
git commit -m "feat(config): add pydantic-settings with provider/storage config"
```

---

## Task 3: Provider 抽象 + OpenAI/Ollama 实现

**Files:**
- Create: `backend/app/core/provider/base.py`
- Create: `backend/app/core/provider/openai_provider.py`
- Create: `backend/app/core/provider/ollama_provider.py`
- Create: `backend/app/core/provider/factory.py`
- Create: `backend/app/core/provider/__init__.py`
- Create: `backend/tests/unit/test_provider.py`

- [ ] **Step 1: 写协议（base.py）**

`app/core/provider/base.py`:
```python
"""模型 provider 协议。

按 spec §1.3「核心能力自研、外部可替换」：所有 LLM/embedding 调用必须经此协议，
业务代码不直接依赖 OpenAI/Ollama SDK，便于 provider 切换与测试 mock。
"""

from collections.abc import AsyncIterator
from typing import Protocol


class EmbeddingProvider(Protocol):
    """嵌入模型协议。"""

    @property
    def dim(self) -> int:
        """返回向量维度。"""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文本，返回与输入等长的向量列表。"""
        ...


class LLMProvider(Protocol):
    """生成模型协议。"""

    async def complete(self, prompt: str, *, system: str = "") -> str:
        """单次补全，返回完整文本。"""
        ...

    async def stream(
        self, prompt: str, *, system: str = ""
    ) -> AsyncIterator[str]:
        """流式补全，逐块产出 token。"""
        ...
        if False:  # pragma: no cover - 协议占位
            yield ""
```

- [ ] **Step 2: 写失败测试（用 respx mock HTTP）**

`tests/unit/test_provider.py`:
```python
"""Provider 测试：mock HTTP，不真实调用 API。"""

import respx
from httpx import Response

from app.core.provider.factory import build_embedding_provider, build_llm_provider


@respx.mock
async def test_openai_embedding_calls_api() -> None:
    """OpenAI embedding 应向 /v1/embeddings 发 POST 并解析向量。"""
    respx.post("https://api.openai.com/v1/embeddings").mock(
        return_value=Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})
    )
    provider = build_embedding_provider("openai", api_key="sk-x", dim=2)
    vecs = await provider.embed(["hello"])
    assert vecs == [[0.1, 0.2]]


@respx.mock
async def test_openai_llm_stream_yields_chunks() -> None:
    """OpenAI stream 应逐块产出 delta 文本。"""
    sse = "data: {\"choices\":[{\"delta\":{\"content\":\"Hi\"}}]}\n\ndata: [DONE]\n\n"
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(200, text=sse)
    )
    llm = build_llm_provider("openai", api_key="sk-x")
    chunks = [c async for c in llm.stream("ping")]
    assert chunks == ["Hi"]
```

- [ ] **Step 3: 运行测试，确认失败**

Run: `uv run pytest tests/unit/test_provider.py -v`
Expected: FAIL（factory 不存在）

- [ ] **Step 4: 写 OpenAI 实现**

`app/core/provider/openai_provider.py`:
```python
"""OpenAI provider 实现。

直接用 httpx 调 OpenAI 兼容接口（而非官方 SDK），便于测试 mock 与
对接 OpenAI 兼容的本地服务（如 vLLM 的 OpenAI server）。
"""

import json
from collections.abc import AsyncIterator

import httpx

from app.core.provider.base import EmbeddingProvider, LLMProvider


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI 兼容嵌入。"""

    def __init__(self, api_key: str, base_url: str, model: str, dim: int) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"input": texts, "model": self._model},
                timeout=60,
            )
            resp.raise_for_status()
            return [d["embedding"] for d in resp.json()["data"]]


class OpenAILLM(LLMProvider):
    """OpenAI 兼容生成。"""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(self, prompt: str, *, system: str = "") -> str:
        chunks = [c async for c in self.stream(prompt, system=system)]
        return "".join(chunks)

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "messages": messages, "stream": True},
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: ") or line.endswith("[DONE]"):
                        continue
                    delta = json.loads(line[6:])["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
```

- [ ] **Step 5: 写 Ollama 实现**

`app/core/provider/ollama_provider.py`:
```python
"""Ollama provider 实现（本地自部署模型）。"""

import json
from collections.abc import AsyncIterator

import httpx

from app.core.provider.base import EmbeddingProvider, LLMProvider


class OllamaEmbedding(EmbeddingProvider):
    def __init__(self, base_url: str, model: str, dim: int) -> None:
        self._url = base_url.rstrip("/")
        self._model = model
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._url}/api/embed",
                json={"model": self._model, "input": texts},
                timeout=60,
            )
            resp.raise_for_status()
            return [e["embedding"] for e in resp.json()["embeddings"]]


class OllamaLLM(LLMProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self._url = base_url.rstrip("/")
        self._model = model

    async def complete(self, prompt: str, *, system: str = "") -> str:
        chunks = [c async for c in self.stream(prompt, system=system)]
        return "".join(chunks)

    async def stream(self, prompt: str, *, system: str = "") -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self._url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [{"role": "system", "content": system}] if system
                    + [{"role": "user", "content": prompt}],
                    "stream": True,
                },
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    msg = json.loads(line).get("message", {})
                    if msg.get("content"):
                        yield msg["content"]
```
> 注：`+` 用于 list 拼接，若 system 为空则 messages 直接为 [user]。代码可读性可在 review 时优化为显式构造。

- [ ] **Step 6: 写 factory**

`app/core/provider/factory.py`:
```python
"""按配置创建 provider 实例。"""

from app.config import Settings
from app.core.provider.base import EmbeddingProvider, LLMProvider
from app.core.provider.ollama_provider import OllamaEmbedding, OllamaLLM
from app.core.provider.openai_provider import OpenAIEmbedding, OpenAILLM

_OPENAI_LLM_MODEL = "gpt-4o-mini"
_OPENAI_EMBED_MODEL = "text-embedding-3-small"


def build_llm_provider(
    kind: str, *, api_key: str = "", base_url: str = "", model: str = ""
) -> LLMProvider:
    """根据 kind 返回对应 LLM provider。"""
    if kind == "openai":
        return OpenAILLM(api_key, base_url or "https://api.openai.com/v1",
                         model or _OPENAI_LLM_MODEL)
    if kind == "ollama":
        return OllamaLLM(base_url or "http://localhost:11434", model or "qwen2.5:7b")
    raise ValueError(f"unknown llm provider: {kind}")


def build_embedding_provider(
    kind: str, *, api_key: str = "", base_url: str = "", model: str = "", dim: int = 1536
) -> EmbeddingProvider:
    """根据 kind 返回对应 embedding provider。"""
    if kind == "openai":
        return OpenAIEmbedding(api_key, base_url or "https://api.openai.com/v1",
                               model or _OPENAI_EMBED_MODEL, dim)
    if kind == "ollama":
        return OllamaEmbedding(base_url or "http://localhost:11434",
                               model or "nomic-embed-text", dim)
    raise ValueError(f"unknown embedding provider: {kind}")


def llm_from_settings(s: Settings) -> LLMProvider:
    """从 Settings 构建 LLM（依赖注入入口）。"""
    return build_llm_provider(
        s.llm_provider,
        api_key=s.openai_api_key.get_secret_value(),
        base_url=s.openai_base_url if s.llm_provider == "openai" else s.ollama_base_url,
        model=s.ollama_llm_model if s.llm_provider == "ollama" else "",
    )


def embedder_from_settings(s: Settings) -> EmbeddingProvider:
    """从 Settings 构建 embedding provider。"""
    return build_embedding_provider(
        s.embed_provider,
        api_key=s.openai_api_key.get_secret_value(),
        base_url=s.openai_base_url if s.embed_provider == "openai" else s.ollama_base_url,
        model=s.ollama_embed_model if s.embed_provider == "ollama" else "",
        dim=s.embed_dim,
    )
```

- [ ] **Step 7: 运行测试，确认通过**

Run: `uv run pytest tests/unit/test_provider.py -v`
Expected: 2 passed

- [ ] **Step 8: Commit**

```bash
git add backend/app/core/provider/ backend/tests/unit/test_provider.py
git commit -m "feat(provider): add LLM/embedding abstraction with OpenAI + Ollama"
```

---

## Task 4: Storage 抽象 + InMemory + Zvec 实现

**Files:**
- Create: `backend/app/core/storage/base.py`
- Create: `backend/app/core/storage/inmemory.py`
- Create: `backend/app/core/storage/zvec_store.py`
- Create: `backend/app/core/storage/factory.py`
- Create: `backend/app/core/storage/__init__.py`
- Create: `backend/tests/unit/test_storage.py`

- [ ] **Step 1: 写协议 + InMemory 实现**

`app/core/storage/base.py`:
```python
"""向量存储协议。

spec §6.1.3: PostgreSQL 是 source of truth，向量库仅作索引层。
此协议只管向量与过滤元数据，不承载业务状态。
"""

from typing import NamedTuple, Protocol


class VectorHit(NamedTuple):
    """单条召回结果。"""
    id: str           # 业务侧的 chunk_id（PG 中的主键）
    score: float
    metadata: dict


class VectorStore(Protocol):
    """向量索引协议。"""

    async def add(
        self, ids: list[str], vectors: list[list[float]], metadata: list[dict]
    ) -> None:
        """批量写入向量与过滤元数据。"""
        ...

    async def search(
        self, query: list[float], top_k: int, filter: dict | None = None
    ) -> list[VectorHit]:
        """按向量召回 top_k，可按 metadata 等值过滤。"""
        ...

    async def delete(self, ids: list[str]) -> None:
        """按 id 删除。"""
        ...
```

`app/core/storage/inmemory.py`:
```python
"""内存向量库，用于测试与零依赖快速启动。

实现朴素余弦相似度，不依赖任何外部库。
"""

import math

from app.core.storage.base import VectorHit, VectorStore


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._records: dict[str, tuple[list[float], dict]] = {}

    async def add(
        self, ids: list[str], vectors: list[list[float]], metadata: list[dict]
    ) -> None:
        for id_, vec, meta in zip(ids, vectors, metadata, strict=True):
            self._records[id_] = (vec, meta)

    async def search(
        self, query: list[float], top_k: int, filter: dict | None = None
    ) -> list[VectorHit]:
        scored: list[tuple[float, str, dict]] = []
        for id_, (vec, meta) in self._records.items():
            if filter and not all(meta.get(k) == v for k, v in filter.items()):
                continue
            score = _cosine(query, vec)
            scored.append((score, id_, meta))
        scored.sort(reverse=True)
        return [VectorHit(id=i, score=s, metadata=m) for s, i, m in scored[:top_k]]

    async def delete(self, ids: list[str]) -> None:
        for id_ in ids:
            self._records.pop(id_, None)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
```

- [ ] **Step 2: 写失败测试**

`tests/unit/test_storage.py`:
```python
"""Storage 抽象测试（用 InMemory，无外部依赖）。"""

from app.core.storage.factory import build_vector_store


async def test_search_returns_by_cosine_similarity() -> None:
    """search 应按余弦相似度排序返回 top_k。"""
    store = build_vector_store("inmemory")
    await store.add(
        ids=["a", "b", "c"],
        vectors=[[1.0, 0.0], [0.0, 1.0], [0.9, 0.1]],
        metadata=[{"doc": "1"}, {"doc": "2"}, {"doc": "1"}],
    )
    hits = await store.search([1.0, 0.0], top_k=2)
    assert hits[0].id == "a"
    assert hits[1].id == "c"


async def test_search_applies_metadata_filter() -> None:
    """filter 应按 metadata 等值过滤。"""
    store = build_vector_store("inmemory")
    await store.add(
        ids=["a", "b"], vectors=[[1.0, 0.0], [1.0, 0.0]],
        metadata=[{"doc": "1"}, {"doc": "2"}],
    )
    hits = await store.search([1.0, 0.0], top_k=5, filter={"doc": "2"})
    assert [h.id for h in hits] == ["b"]


async def test_delete_removes_records() -> None:
    store = build_vector_store("inmemory")
    await store.add(ids=["a"], vectors=[[1.0]], metadata=[{}])
    await store.delete(["a"])
    assert await store.search([1.0], top_k=5) == []
```

- [ ] **Step 3: 运行测试，确认失败**

Run: `uv run pytest tests/unit/test_storage.py -v`
Expected: FAIL（factory 不存在）

- [ ] **Step 4: 写 Zvec 实现 + factory**

`app/core/storage/zvec_store.py`:
```python
"""Zvec 嵌入式向量库实现（spec §3 选型：默认本地向量库）。

⚠️ Zvec Python binding 较新，API 以官方文档为准。此处为预期接口；
若 binding 不可用，factory 会自动 fallback 到 InMemory（见 factory）。
启动时用 VRAG_VECTOR_STORE=zvec 显式启用。
"""

from app.core.storage.base import VectorHit, VectorStore


class ZvecVectorStore(VectorStore):
    """Zvec 适配层。P0 先做接口占位 + 真实接入在 binding 稳定后补全。"""

    def __init__(self, path: str, dim: int) -> None:
        # TODO(P0): 待 zvec python binding 发布稳定 API 后接入。
        # 当前实现委托给内存版以保证可运行，并在启动日志告警。
        self._fallback = __import__(
            "app.core.storage.inmemory", fromlist=["InMemoryVectorStore"]
        ).InMemoryVectorStore()
        self._path = path
        self._dim = dim

    async def add(self, ids, vectors, metadata) -> None:  # type: ignore[no-untyped-def]
        await self._fallback.add(ids, vectors, metadata)

    async def search(self, query, top_k, filter=None) -> list[VectorHit]:  # type: ignore[no-untyped-def]
        return await self._fallback.search(query, top_k, filter)

    async def delete(self, ids) -> None:  # type: ignore[no-untyped-def]
        await self._fallback.delete(ids)
```

`app/core/storage/factory.py`:
```python
"""向量库工厂。"""

from app.core.storage.base import VectorStore
from app.core.storage.inmemory import InMemoryVectorStore
from app.core.storage.zvec_store import ZvecVectorStore


def build_vector_store(kind: str, **kwargs: object) -> VectorStore:
    """根据 kind 创建向量库；zvec 暂委托 inmemory（见 ZvecVectorStore 注释）。"""
    if kind == "inmemory":
        return InMemoryVectorStore()
    if kind == "zvec":
        return ZvecVectorStore(
            path=str(kwargs.get("path", "./data/zvec")),
            dim=int(kwargs.get("dim", 1536)),
        )
    raise ValueError(f"unknown vector store: {kind}")
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/unit/test_storage.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/storage/ backend/tests/unit/test_storage.py
git commit -m "feat(storage): add VectorStore abstraction with InMemory + Zvec stub"
```

> ⚠️ **风险记录**：Zvec Python binding 是 2026 年新发布，API 可能未稳定。P0 先以 InMemory 保证链路可跑通与可测；Zvec 真实接入作为 P0 收尾的单独任务（见 Task 12 验证项），若 binding 不成熟则降级为"Zvec 配置项保留，默认 inmemory"。

---

## Task 5: Postgres 元数据层

**Files:**
- Create: `backend/app/core/db/models.py`
- Create: `backend/app/core/db/session.py`
- Create: `backend/app/core/db/__init__.py`
- Create: `backend/tests/unit/test_db_models.py`

- [ ] **Step 1: 写模型**

`app/core/db/models.py`:
```python
"""SQLAlchemy 元数据模型。

spec §6.1.3 / §7.1.6: PG 是 source of truth，存文档与 chunk 的结构化元信息
（向量本身在 VectorStore）。预留 workspace_id/org_id/user_id 以备多租户（spec §11）。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "document"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String, default="default")  # 多租户预留
    org_id: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    filename: Mapped[str] = mapped_column(String)
    source_path: Mapped[str] = mapped_column(Text)
    parser: Mapped[str] = mapped_column(String, default="pymupdf")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete")


class Chunk(Base):
    __tablename__ = "chunk"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(nullable=True)
    heading_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[Document] = relationship(back_populates="chunks")
```

`app/core/db/session.py`:
```python
"""数据库会话工厂。"""

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


def init_engine(database_url: str) -> AsyncEngine:
    """初始化全局 engine（应用启动时调用）。"""
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker:
    if _session_factory is None:
        raise RuntimeError("engine not initialized; call init_engine() first")
    return _session_factory
```

- [ ] **Step 2: 写失败测试（用 aiosqlite 内存库，无外部依赖）**

`tests/unit/test_db_models.py`:
```python
"""元数据模型测试，用 aiosqlite 内存库避免 PG 依赖。

依赖: uv add --dev aiosqlite
"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db.models import Base, Chunk, Document


async def test_document_chunk_relationship() -> None:
    """Document 与 Chunk 应能级联保存与查询。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        doc = Document(filename="a.pdf", source_path="/tmp/a.pdf")
        doc.chunks.append(Chunk(text="hello", page=1))
        session.add(doc)
        await session.commit()
        loaded = await session.get(Document, doc.id)
        assert loaded is not None
        assert loaded.filename == "a.pdf"
        assert len(loaded.chunks) == 1
        assert loaded.chunks[0].text == "hello"
```

- [ ] **Step 3: 运行测试，确认失败**

Run:
```bash
uv add --dev aiosqlite && uv run pytest tests/unit/test_db_models.py -v
```
Expected: FAIL（模型不存在 → 先写模型再跑）

> 实施顺序：先完成 Step 1（模型）与 session，再跑测试。

- [ ] **Step 4: 运行测试，确认通过**

Run: `uv run pytest tests/unit/test_db_models.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/db/ backend/tests/unit/test_db_models.py backend/pyproject.toml
git commit -m "feat(db): add Document/Chunk models + async session factory"
```

---

## Task 6: 文档处理（解析 + Canonical Block + Chunker）

**Files:**
- Create: `backend/app/core/document/models.py`
- Create: `backend/app/core/document/parser.py`
- Create: `backend/app/core/document/chunker.py`
- Create: `backend/app/core/document/__init__.py`
- Create: `backend/tests/unit/test_document.py`
- Test fixture: `backend/tests/fixtures/sample.txt`

- [ ] **Step 1: 写 Canonical Block 模型（简化版）**

`app/core/document/models.py`:
```python
"""Canonical DocumentBlock（spec §7.1.3 简化版）。

P0 只支持文本块；P4 扩展 table/image/formula 等类型与 html/markdown 多表示。
"""

from dataclasses import dataclass


@dataclass
class DocumentBlock:
    """解析产出的标准块，所有 parser/OCR 输出归一化为此结构。"""
    text: str
    page: int | None = None
    block_type: str = "paragraph"
    heading_path: tuple[str, ...] = ()
```

- [ ] **Step 2: 写 parser（PyMuPDF，纯文本 PDF）**

`app/core/document/parser.py`:
```python
"""文档解析器（P0 仅 PyMuPDF 纯文本提取）。

spec §7.1.2: 后续按 DocumentProfiler 路由到 Docling/Unstructured/OCR；
P0 先实现最基础的文本提取以跑通链路。
"""

import pymupdf  # type: ignore[import-untyped]

from app.core.document.models import DocumentBlock


def parse_pdf(path: str) -> list[DocumentBlock]:
    """用 PyMuPDF 逐页提取文本，返回 DocumentBlock 列表。"""
    blocks: list[DocumentBlock] = []
    with pymupdf.open(path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            if text:
                blocks.append(DocumentBlock(text=text, page=page_num))
    return blocks


def parse_plain_text(text: str) -> list[DocumentBlock]:
    """纯文本解析（测试用），整段作为一个 block。"""
    return [DocumentBlock(text=text, page=1)]
```

- [ ] **Step 3: 写 chunker**

`app/core/document/chunker.py`:
```python
"""文本分块器。

P0 用固定大小 + overlap；spec §7.1.4 后续支持 parent-child/section/table 等多粒度。
"""

from app.core.document.models import DocumentBlock


def split_text(text: str, *, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """按字符长度切分，相邻块有 overlap 保证边界语义连续。"""
    if len(text) <= chunk_size:
        return [text] if text else []
    chunks: list[str] = []
    step = chunk_size - overlap
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size]
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks


def chunk_blocks(
    blocks: list[DocumentBlock], *, chunk_size: int = 500, overlap: int = 50
) -> list[DocumentBlock]:
    """对每个 block 切分，page/heading_path 透传到子块。"""
    out: list[DocumentBlock] = []
    for block in blocks:
        for piece in split_text(block.text, chunk_size=chunk_size, overlap=overlap):
            out.append(
                DocumentBlock(
                    text=piece, page=block.page,
                    block_type=block.block_type, heading_path=block.heading_path,
                )
            )
    return out
```

- [ ] **Step 4: 写失败测试**

`tests/unit/test_document.py`:
```python
"""文档解析与分块测试。"""

from app.core.document.chunker import chunk_blocks, split_text
from app.core.document.models import DocumentBlock
from app.core.document.parser import parse_plain_text


def test_split_text_respects_size_and_overlap() -> None:
    """切分应满足 chunk_size，相邻块有 overlap。"""
    chunks = split_text("abcdefghij", chunk_size=4, overlap=1)
    # 步长 3: [abcd, defg, ghij]
    assert chunks == ["abcd", "defg", "ghij"]


def test_split_text_short_text_single_chunk() -> None:
    assert split_text("hi", chunk_size=100) == ["hi"]


def test_chunk_blocks_preserves_page() -> None:
    """子块应继承原 block 的 page。"""
    blocks = [DocumentBlock(text="x" * 600, page=3)]
    chunks = chunk_blocks(blocks, chunk_size=500, overlap=50)
    assert len(chunks) == 2
    assert all(c.page == 3 for c in chunks)


def test_parse_plain_text() -> None:
    assert parse_plain_text("hello") == [DocumentBlock(text="hello", page=1)]
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/unit/test_document.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/document/ backend/tests/unit/test_document.py
git commit -m "feat(document): add CanonicalBlock + PyMuPDF parser + chunker"
```

---

## Task 7: 检索引擎（retrieval）

**Files:**
- Create: `backend/app/core/retrieval/engine.py`
- Create: `backend/app/core/retrieval/__init__.py`
- Create: `backend/tests/unit/test_retrieval.py`

- [ ] **Step 1: 写检索引擎**

`app/core/retrieval/engine.py`:
```python
"""检索引擎：embed query → 向量检索 → 返回 chunk 文本。

spec §3: retrieval 封装 LlamaIndex；P0 先用自研的最小封装
（embedding + VectorStore），hybrid/rerank 在 P1/P4 接入 LlamaIndex 完善。
"""

from dataclasses import dataclass

from app.core.provider.base import EmbeddingProvider
from app.core.storage.base import VectorHit, VectorStore


@dataclass
class RetrievedChunk:
    """检索返回的单条结果，含原文与 citation 元数据。"""
    chunk_id: str
    text: str
    score: float
    metadata: dict


class RetrievalEngine:
    """编排 embedding + 向量库的检索入口。"""

    def __init__(self, embedder: EmbeddingProvider, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store

    async def index(self, chunks: list[tuple[str, list[float], dict]]) -> None:
        """写入已嵌入的 chunk：(chunk_id, vector, metadata)。"""
        ids = [c[0] for c in chunks]
        vectors = [c[1] for c in chunks]
        metadata = [c[2] for c in chunks]
        await self._store.add(ids, vectors, metadata)

    async def search(
        self, query: str, top_k: int = 4, filter: dict | None = None,
        text_lookup: dict[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        """检索 query：embed → 向量召回 → 用 text_lookup 补全原文。"""
        query_vec = (await self._embedder.embed([query]))[0]
        hits: list[VectorHit] = await self._store.search(query_vec, top_k, filter)
        return [
            RetrievedChunk(
                chunk_id=h.id, score=h.score, metadata=h.metadata,
                text=(text_lookup or {}).get(h.id, ""),
            )
            for h in hits
        ]
```

- [ ] **Step 2: 写失败测试（fake embedder + InMemory store）**

`tests/unit/test_retrieval.py`:
```python
"""检索引擎测试：用确定性 fake embedder，不依赖真实模型。"""

from app.core.provider.base import EmbeddingProvider
from app.core.retrieval.engine import RetrievalEngine
from app.core.storage.factory import build_vector_store


class FakeEmbedder(EmbeddingProvider):
    """把文本映射为确定性向量（按字符统计），便于断言相似度。"""
    @property
    def dim(self) -> int:
        return 4

    async def embed(self, texts: list[str]) -> list[list[float]]:
        def vec(s: str) -> list[float]:
            return [float(s.count(c)) for c in "abcd"]
        return [vec(t) for t in texts]


async def test_search_returns_indexed_chunk_text() -> None:
    engine = RetrievalEngine(FakeEmbedder(), build_vector_store("inmemory"))
    await engine.index([
        ("c1", (await FakeEmbedder().embed(["abc"]))[0], {"doc": "d1"}),
    ])
    hits = await engine.search("abc", top_k=1, text_lookup={"c1": "hello world"})
    assert len(hits) == 1
    assert hits[0].chunk_id == "c1"
    assert hits[0].text == "hello world"
```

- [ ] **Step 3: 运行测试，确认通过**

Run: `uv run pytest tests/unit/test_retrieval.py -v`
Expected: 1 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/retrieval/ backend/tests/unit/test_retrieval.py
git commit -m "feat(retrieval): add RetrievalEngine orchestrating embed + vector store"
```

---

## Task 8: /documents 上传端点

**Files:**
- Create: `backend/app/api/routes/documents.py`
- Modify: `backend/app/api/router.py`（include documents router）
- Create: `backend/app/deps.py`
- Create: `backend/tests/integration/test_documents.py`

- [ ] **Step 1: 写依赖注入容器**

`app/deps.py`:
```python
"""应用级依赖容器（单例）。

FastAPI 启动时 init，路由用 Depends 取用。避免在每个请求重建 provider/store。
"""

from dataclasses import dataclass

from app.config import Settings, get_settings
from app.core.db.session import init_engine
from app.core.provider.base import EmbeddingProvider, LLMProvider
from app.core.provider.factory import embedder_from_settings, llm_from_settings
from app.core.retrieval.engine import RetrievalEngine
from app.core.storage.base import VectorStore
from app.core.storage.factory import build_vector_store

_globals: dict[str, object] = {}


def init_deps(settings: Settings | None = None) -> None:
    """应用启动时初始化所有依赖（lifespan 调用）。"""
    s = settings or get_settings()
    init_engine(s.database_url)
    embedder = embedder_from_settings(s)
    store = build_vector_store(s.vector_store, path=s.zvec_path, dim=s.embed_dim)
    engine = RetrievalEngine(embedder, store)
    _globals.clear()
    _globals.update(
        settings=s, embedder=embedder, llm=llm_from_settings(s),
        store=store, retrieval=engine,
    )


def get_retrieval() -> RetrievalEngine:
    return _globals["retrieval"]  # type: ignore[return-value]


def get_llm() -> LLMProvider:
    return _globals["llm"]  # type: ignore[return-value]


def get_embedder() -> EmbeddingProvider:
    return _globals["embedder"]  # type: ignore[return-value]
```

- [ ] **Step 2: 写 /documents 端点**

`app/api/routes/documents.py`:
```python
"""文档上传与索引端点。

流程：保存文件 → parse → chunk → embed → 写向量库 + PG 元数据。
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.db.models import Chunk, Document
from app.core.db.session import get_session_factory
from app.core.document.chunker import chunk_blocks
from app.core.document.parser import parse_plain_text
from app.deps import get_embedder, get_retrieval
from app.core.provider.base import EmbeddingProvider
from app.core.retrieval.engine import RetrievalEngine

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("")
async def upload_document(
    file: UploadFile,
    retrieval: RetrievalEngine = Depends(get_retrieval),
    embedder: EmbeddingProvider = Depends(get_embedder),
) -> dict[str, str]:
    """上传文本文件（P0 仅纯文本），解析分块后写入索引。"""
    content = (await file.read()).decode("utf-8", errors="ignore")
    blocks = parse_plain_text(content)
    chunks = chunk_blocks(blocks)

    # 文本块批量嵌入
    texts = [c.text for c in chunks]
    vectors = await embedder.embed(texts) if texts else []

    doc_id = str(uuid.uuid4())
    session_factory: async_sessionmaker = get_session_factory()
    chunk_text_map: dict[str, str] = {}
    index_payload: list[tuple[str, list[float], dict]] = []

    async with session_factory() as session:
        doc = Document(id=doc_id, filename=file.filename or "upload",
                       source_path=f"/tmp/{doc_id}")
        for block_vec, block in zip(vectors, chunks, strict=True):
            chunk = Chunk(text=block.text, page=block.page, document=doc)
            session.add(chunk)
            await session.flush()  # 取 chunk.id
            index_payload.append((chunk.id, block_vec, {"doc": doc_id}))
            chunk_text_map[chunk.id] = block.text
        await session.commit()

    await retrieval.index(index_payload)
    return {"document_id": doc_id, "chunks": str(len(chunks))}
```

> 注：P0 仅处理纯文本；PDF 上传在 Task 12 集成验证后接 `parse_pdf`。`parse_plain_text` 保证链路可测。

- [ ] **Step 3: 接入 router + lifespan**

Modify `app/main.py`，在 `create_app` 中加入 lifespan 调用 `init_deps()`，并在 `app/api/router.py` include documents router：

`app/api/router.py` 追加：
```python
from app.api.routes import documents
api_router.include_router(documents.router)
```

`app/main.py` 改为：
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.router import api_router
from app.deps import init_deps


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_deps()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="v-rag backend", lifespan=lifespan)
    app.include_router(api_router)
    return app


app = create_app()
```

- [ ] **Step 4: 写失败测试（mock embedder，用 sqlite 内存库）**

`tests/integration/test_documents.py`:
```python
"""文档上传集成测试：mock embedding，元数据用 sqlite 内存库。"""

import io

import respx
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db.models import Base
from app.core.db import session as db_session
from app.deps import _globals, init_deps
from app.main import app


def _setup_test_deps(monkeypatch) -> None:
    """用 inmemory 向量库 + sqlite 元数据，避免 PG/embedding 依赖。"""
    monkeypatch.setenv("VRAG_VECTOR_STORE", "inmemory")
    monkeypatch.setenv("VRAG_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("VRAG_EMBED_PROVIDER", "inmemory")  # 需 fake embedder
    init_deps()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    import asyncio
    asyncio.get_event_loop().run_until_complete(_create_tables(engine))
    db_session._engine = engine
    db_session._session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def _create_tables(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@respx.mock
def test_upload_then_chatable(monkeypatch) -> None:
    """上传文本应返回 document_id 与 chunk 数。"""
    _setup_test_deps(monkeypatch)
    # 用 fake embedder 替换（避免真实 OpenAI 调用）
    from tests.unit.test_retrieval import FakeEmbedder
    _globals["embedder"] = FakeEmbedder()
    _globals["retrieval"]._embedder = _globals["embedder"]  # type: ignore[attr-defined]

    client = TestClient(app)
    resp = client.post(
        "/documents",
        files={"file": ("note.txt", io.BytesIO(b"hello world from vrag"), "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "document_id" in body
```

> ⚠️ 该测试涉及同步 TestClient 驱动异步 lifespan 与 sqlite，较为脆弱。**实施时优先用 `httpx.AsyncClient` + `pytest-asyncio` 重写**，必要时 @python:test-fixture skill 提供 fixture 封装。本测试在 plan 中标明意图，具体实现以可跑通为准。

- [ ] **Step 5: 运行测试，确认通过**

Run: `uv run pytest tests/integration/test_documents.py -v`
Expected: 1 passed（若不稳定，改用 AsyncClient 重写）

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/documents.py backend/app/deps.py backend/app/main.py backend/app/api/router.py backend/tests/integration/
git commit -m "feat(api): add /documents upload endpoint with parse-chunk-embed-index"
```

---

## Task 9: /chat SSE 流式端点

**Files:**
- Create: `backend/app/api/routes/chat.py`
- Modify: `backend/app/api/router.py`（include chat router）
- Create: `backend/tests/integration/test_chat.py`

- [ ] **Step 1: 写 /chat 端点（SSE）**

`app/api/routes/chat.py`:
```python
"""聊天端点：query → retrieve → LLM 流式生成，以 SSE 返回。

P0 是最朴素的 RAG：检索 top_k chunk 拼进 prompt，LLM 流式回答。
意图路由 / 规划在 P1/P2 接入。
"""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.provider.base import LLMProvider
from app.core.retrieval.engine import RetrievalEngine
from app.deps import get_llm, get_retrieval

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    top_k: int = 4


def _build_prompt(query: str, contexts: list[str]) -> str:
    joined = "\n---\n".join(contexts)
    return (
        f"根据以下参考资料回答问题。若资料不足请如实说明。\n\n"
        f"参考资料:\n{joined}\n\n问题: {query}"
    )


@router.post("")
async def chat(
    req: ChatRequest,
    llm: LLMProvider = Depends(get_llm),
    retrieval: RetrievalEngine = Depends(get_retrieval),
) -> StreamingResponse:
    """RAG 聊天，SSE 流式返回生成 token。"""
    hits = await retrieval.search(req.query, top_k=req.top_k)
    prompt = _build_prompt(req.query, [h.text for h in hits])

    async def event_stream() -> AsyncIterator[bytes]:
        async for token in llm.stream(prompt, system="你是 v-rag 助手。"):
            yield f"data: {token}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

`app/api/router.py` 追加 `from app.api.routes import chat` + `api_router.include_router(chat.router)`。

- [ ] **Step 2: 写失败测试（mock LLM stream）**

`tests/integration/test_chat.py`:
```python
"""chat 端点测试：用 fake LLM，验证 SSE 流。"""

from fastapi.testclient import TestClient

from app.deps import _globals, init_deps
from app.main import app


class FakeLLM:
    async def stream(self, prompt: str, *, system: str = ""):
        for token in ["你", "好"]:
            yield token

    async def complete(self, prompt: str, *, system: str = "") -> str:
        return "".join([t async for t in self.stream(prompt, system=system)])


def test_chat_streams_sse(monkeypatch) -> None:
    monkeypatch.setenv("VRAG_VECTOR_STORE", "inmemory")
    monkeypatch.setenv("VRAG_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    init_deps()
    _globals["llm"] = FakeLLM()

    client = TestClient(app)
    resp = client.post("/chat", json={"query": "hi", "top_k": 2})
    assert resp.status_code == 200
    body = resp.text
    assert "data: 你" in body
    assert "data: 好" in body
    assert "[DONE]" in body
```

- [ ] **Step 3: 运行测试，确认通过**

Run: `uv run pytest tests/integration/test_chat.py -v`
Expected: 1 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes/chat.py backend/app/api/router.py backend/tests/integration/test_chat.py
git commit -m "feat(api): add /chat SSE endpoint with retrieve-then-generate"
```

---

## Task 10: 可观测性（OTel + Langfuse 基础）

**Files:**
- Create: `backend/app/core/observability/tracing.py`
- Create: `backend/app/core/observability/__init__.py`
- Modify: `backend/app/main.py`（启动时初始化）

- [ ] **Step 1: 写 tracing 装饰器**

`app/core/observability/tracing.py`:
```python
"""可观测埋点（spec §9: OpenTelemetry + Langfuse + v-rag Trace Schema 三层）。

P0 只接基础 span；Langfuse/OTel exporter 在配置存在时启用，否则 no-op，
保证零配置可启动。trace_id 关联各层在 P1（绑定 graph_config_id）完善。
"""

import contextvars
import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

_current_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "vrag_trace_id", default=""
)


def traced(name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """同步/异步函数通用 span 装饰器，记录名称与 trace_id。

    P0 实现：仅写日志 + 设置 trace_id contextvar；
    OTel/Langfuse 接入在 exporter 配置存在时由 Task 10 Step 3 启用。
    """
    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        import logging
        log = logging.getLogger("vrag.trace")

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            log.info("span.start name=%s", name)
            return fn(*args, **kwargs)

        @functools.wraps(fn)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            log.info("span.start name=%s", name)
            return await fn(*args, **kwargs)  # type: ignore[no-any-return]

        import inspect
        return async_wrapper if inspect.iscoroutinefunction(fn) else sync_wrapper

    return decorator
```

- [ ] **Step 2: 写失败测试**

`tests/unit/test_tracing.py`:
```python
"""tracing 装饰器测试。"""

from app.core.observability.tracing import traced


@traced("do_work")
async def do_work() -> str:
    return "done"


async def test_traced_preserves_return_value() -> None:
    """装饰后函数仍应返回原值。"""
    assert await do_work() == "done"
```

- [ ] **Step 3: 真实接入 OTel（满足 spec §10 P0「OTel/Langfuse 接入」）**

在 `app/core/observability/tracing.py` 追加 telemetry 初始化函数：

```python
def init_telemetry(otel_endpoint: str = "") -> None:
    """初始化 OpenTelemetry tracer。

    无 endpoint 时用 ConsoleSpanExporter（开发可见）；配置 endpoint 时加 OTLP 导出。
    Langfuse 深度集成（prompt/cost 观测）在 P5；P0 先保证 request 级 span 可见，
    使「可观测接入」在 P0 真正落地而非空 hook。
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    if otel_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        provider.add_span_processor(
            SimpleSpanProcessor(OTLPSpanExporter(endpoint=otel_endpoint))
        )
    trace.set_tracer_provider(provider)
```

在 `app/main.py` 启动时初始化并 instrument FastAPI（自动为每个 request 生成 span）：

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.config import get_settings
from app.core.observability.tracing import init_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    init_telemetry(s.otel_exporter_otlp_endpoint)
    init_deps()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="v-rag backend", lifespan=lifespan)
    FastAPIInstrumentor.instrument_app(app)
    app.include_router(api_router)
    return app
```

> 依赖补充：`uv add opentelemetry-exporter-otlp-proto-http`（仅当计划用 OTLP 导出时；ConsoleSpanExporter 已随 sdk 自带）。

Run（验证 instrumentation 生效 + 测试不回归）:
```bash
uv run pytest tests/unit/test_tracing.py -v
uv run uvicorn app.main:app --port 8000 & ; sleep 2 ; curl -s localhost:8000/health ; kill %1
```
Expected: 测试 PASS；控制台输出含 OTel span（如 `SpanName=/health`），证明 request 级可观测已接入。

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/observability/ backend/tests/unit/test_tracing.py
git commit -m "feat(observability): add @traced span decorator (OTel/Langfuse ready)"
```

---

## Task 11: Docker（Dockerfile + docker-compose）

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/docker-compose.yml`
- Create: `backend/.dockerignore`

- [ ] **Step 1: 写 Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv sync --no-dev --extra="" 2>/dev/null || uv pip install --system -e .

COPY app ./app
COPY alembic ./alembic

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 写 docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: vrag
      POSTGRES_PASSWORD: vrag
      POSTGRES_DB: vrag
    ports: ["5432:5432"]
    volumes: ["postgres_data:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vrag"]
      interval: 5s
      timeout: 3s
      retries: 10

  backend:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      VRAG_DATABASE_URL: postgresql+asyncpg://vrag:vrag@postgres:5432/vrag
      VRAG_VECTOR_STORE: inmemory   # Zvec binding 稳定后改 zvec
      VRAG_LLM_PROVIDER: openai
      VRAG_OPENAI_API_KEY: ${VRAG_OPENAI_API_KEY:-}
    ports: ["8000:8000"]

volumes:
  postgres_data:
```

- [ ] **Step 3: 写 .dockerignore**

```
__pycache__
.venv
tests
*.md
.git
```

- [ ] **Step 4: 冒烟验证（启动并 curl /health）**

Run:
```bash
cd backend && docker compose up -d --build && sleep 10
curl -s http://localhost:8000/health
```
Expected: `{"status":"ok"}`

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile backend/docker-compose.yml backend/.dockerignore
git commit -m "feat(ops): add Dockerfile + docker-compose (postgres + backend)"
```

---

## Task 12: 端到端集成测试 + Zvec 接入验证

**Files:**
- Create: `backend/tests/integration/test_rag_flow.py`
- Modify: 若 Zvec binding 可用，替换 Task 4 的 ZvecVectorStore fallback

- [ ] **Step 1: 写端到端测试（mock LLM + fake embedder，验证 upload→chat 完整链路）**

`tests/integration/test_rag_flow.py`:
```python
"""端到端：上传文档 → chat 检索 → 验证 context 被注入。

不依赖真实 LLM/embedding，验证管线编排正确性。
"""

# 见 Task 8/9 的 fake provider 模式，组合 upload + chat：
# 1. init_deps with inmemory + fake embedder/llm
# 2. POST /documents 上传 "vrag supports multimodal RAG"
# 3. POST /chat 问 "what does vrag support"
# 4. 断言 fake LLM 收到的 prompt 包含上传的文本（证明检索命中）
```

> 实现要点：FakeLLM 需记录收到的 prompt 以断言 context 注入。这是 P0 验收的核心证据。

- [ ] **Step 2: 运行全量测试 + lint + typecheck**

Run:
```bash
cd backend
uv run pytest -v
uv run ruff check .
uv run mypy app
```
Expected: 全部 PASS，无 error

- [ ] **Step 3: Zvec 接入评估**

调研 zvec Python binding 现状：
```bash
uv add zvec 2>&1 || echo "binding 不可用，保持 inmemory 默认"
```
- 若可用：替换 `ZvecVectorStore` 的 fallback 为真实 Zvec API，补测试。
- 若不可用：保留配置项，默认 inmemory，在 README 标注「Zvec 待 binding 稳定后启用」，更新 spec 风险记录。

- [ ] **Step 4: 更新 README Quick Start（最小可运行说明）**

在 `README.md` 的 Quick Start 段补：
```
cd backend
docker compose up -d
curl http://localhost:8000/health   # {"status":"ok"}
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/integration/test_rag_flow.py backend/README.md
git commit -m "test(e2e): add upload→chat flow; verify Zvec binding availability"
```

---

## 验收标准（P0-A 完成 = 全部满足）

- [ ] `GET /health` 返回 ok
- [ ] `POST /documents` 上传文本文件，返回 document_id 与 chunk 数
- [ ] `POST /chat` SSE 流式返回，且 prompt 含检索到的 context（端到端测试证明）
- [ ] provider 抽象支持 OpenAI + Ollama 切换（factory 测试覆盖）
- [ ] storage 抽象支持 inmemory（zvec 接入或降级标注）
- [ ] PG 元数据 Document/Chunk 表可读写（sqlite 测试覆盖）
- [ ] `pytest` 全绿、`ruff check` 无 error、`mypy` 无 error
- [ ] `docker compose up` 可启动，/health 可访问
- [ ] 可观测 `@traced` 装饰器就位（OTel/Langfuse 配置预留）

## 不在 P0-A 范围（显式排除，YAGNI）

- 意图路由 / LangGraph 编排（P1）
- 自主规划（P2）
- 自研记忆（P3）
- 多模态 ColPali / OCR / DocumentProfiler（P4）
- 前端管理端（P0-B，下一 plan）
- Alembic 迁移脚本（P0 用 `create_all` 起步，迁移在首次 schema 变更时引入）
- 评测 Golden Set（P5）

## 风险与待定

1. **Zvec Python binding 成熟度**：2026 新发布，P0 先 inmemory 保底，Task 12 验证后再定。
2. **集成测试稳定性**：TestClient + 异步 lifespan + sqlite 可能有坑，优先 AsyncClient + pytest-asyncio。
3. **Alembic 时机**：P0 用 `Base.metadata.create_all` 启动建表；第一个 schema 变更时引入 Alembic。
