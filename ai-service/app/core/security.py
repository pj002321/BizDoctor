# [역할] 내부망 인증 — X-Service-Token 헤더를 검사해 Next.js 서버만 호출하게 막는다.
"""내부망 호출 인증 — Next.js 서버만 `X-Service-Token` 헤더로 이 서버를 부른다(AGENTS.md)."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 타이밍 공격에 안전한 문자열 비교(compare_digest)를 쓰기 위해 가져온다.
import hmac

# Header: 요청 헤더 읽기, HTTPException: 오류 응답, status: 상태 코드 상수.
from fastapi import Header, HTTPException, status

# 기대하는 토큰 값(SERVICE_TOKEN)을 읽을 설정 모듈.
from app.core import config


# 모든 라우트에 걸리는 의존성. X-Service-Token 헤더 값을 인자로 받는다(없으면 None).
def require_service_token(x_service_token: str | None = Header(default=None)) -> None:
    # 환경변수에 설정된 정답 토큰을 꺼낸다.
    expected = config.SERVICE_TOKEN
    # 토큰이 설정돼 있지 않으면(로컬 개발) 검사를 건너뛴다.
    if not expected:  # 로컬 개발: 토큰 미설정이면 검사하지 않는다
        # 아무것도 하지 않고 통과시킨다.
        return
    # 헤더가 없거나, 정답과 다르면(상수 시간 비교) 거절한다.
    if not x_service_token or not hmac.compare_digest(x_service_token, expected):
        # 401 Unauthorized 로 응답한다.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid service token")
