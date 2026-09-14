import os

import jwt
from jwt import PyJWKClient
from fastapi import Header
from starlette.exceptions import HTTPException


def require_admin_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    # 只有配置 ADMIN_API_KEY 后才强制校验，方便本地开发。
    """可选管理员校验：配置 ADMIN_API_KEY 后才强制校验。"""
    expected = os.getenv("ADMIN_API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="管理员 API Key 无效")


_jwks_client: PyJWKClient | None = None


def require_user_token(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    # OIDC 是可选增强：没有配置 JWKS 时不做校验，保证默认可用。
    """可选 OIDC 校验：配置 OIDC_JWKS_URL 后才强制校验 Bearer Token。"""
    jwks_url = os.getenv("OIDC_JWKS_URL")
    if not jwks_url:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少 Bearer Token")

    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(jwks_url)

    token = authorization.removeprefix("Bearer ").strip()
    signing_key = _jwks_client.get_signing_key_from_jwt(token)
    options = {"verify_aud": bool(os.getenv("OIDC_AUDIENCE"))}
    jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience=os.getenv("OIDC_AUDIENCE"),
        issuer=os.getenv("OIDC_ISSUER"),
        options=options,
    )
