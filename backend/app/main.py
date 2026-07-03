"""FastAPI 应用入口。"""

from fastapi import FastAPI

from app.api.router import api_router


def create_app() -> FastAPI:
    """创建并装配 FastAPI 应用实例。

    Returns:
        已注册全部路由的 FastAPI 应用实例，供 uvicorn 启动与测试使用。
    """
    app = FastAPI(title="v-rag backend")
    app.include_router(api_router)
    return app


app = create_app()
