import os

from fastapi import Header
from starlette.exceptions import HTTPException


def require_admin_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """可选管理员校验：配置 ADMIN_API_KEY 后才强制校验。"""
    expected = os.getenv("ADMIN_API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="管理员 API Key 无效")
