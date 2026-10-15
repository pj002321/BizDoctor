"""내부망 호출 인증 — Next.js 서버만 `X-Service-Token` 헤더로 이 서버를 부른다(AGENTS.md)."""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from app.core import config


def require_service_token(x_service_token: str | None = Header(default=None)) -> None:
    expected = config.SERVICE_TOKEN
    if not expected:
        return
    if not x_service_token or not hmac.compare_digest(x_service_token, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid service token")
