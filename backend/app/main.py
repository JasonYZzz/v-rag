"""FastAPI 应用入口。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.deps import init_deps


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize application dependencies."""

    init_deps()
    yield


def create_app() -> FastAPI:
    """创建并装配 FastAPI 应用实例。

    Returns:
        已注册全部路由的 FastAPI 应用实例，供 uvicorn 启动与测试使用。
    """
    app = FastAPI(title="v-rag backend", lifespan=lifespan)
    app.include_router(api_router)
    return app


app = create_app()
