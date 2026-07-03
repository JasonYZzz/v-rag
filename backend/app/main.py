"""FastAPI 应用入口。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.router import api_router
from app.config import get_settings
from app.core.db.session import migrate_schema
from app.core.observability.tracing import init_telemetry
from app.deps import init_deps


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize application dependencies."""

    settings = get_settings()
    init_telemetry(settings.otel_exporter_otlp_endpoint)
    init_deps()
    await migrate_schema(settings.database_url)
    yield


def create_app() -> FastAPI:
    """创建并装配 FastAPI 应用实例。

    Returns:
        已注册全部路由的 FastAPI 应用实例，供 uvicorn 启动与测试使用。
    """
    app = FastAPI(title="v-rag backend", lifespan=lifespan)
    FastAPIInstrumentor.instrument_app(app)
    app.include_router(api_router)
    return app


app = create_app()
