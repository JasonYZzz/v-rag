"""健康检查端点。"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """返回服务存活状态，供 docker-compose 健康检查与探针使用。

    Returns:
        包含 status 字段的字典，值为 "ok" 表示服务正常。
    """
    return {"status": "ok"}
