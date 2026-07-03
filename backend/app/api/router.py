"""聚合所有路由。"""

from fastapi import APIRouter

from app.api.routes import chat, config, documents, graphs, health, memories, runs

api_router = APIRouter()
api_router.include_router(chat.router)
api_router.include_router(config.router)
api_router.include_router(documents.router)
api_router.include_router(graphs.router)
api_router.include_router(health.router)
api_router.include_router(memories.router)
api_router.include_router(runs.router)
