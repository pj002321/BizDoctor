# [역할] 앱 진입점 — FastAPI 앱 생성, 라우터·토큰 검사 등록, 서비스 예외를 HTTP 상태코드로 변환한다.
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# Depends: 의존성 주입, FastAPI: 앱 클래스, Request: 요청 객체, status: 상태 코드 상수.
from fastapi import Depends, FastAPI, Request, status
# JSON 본문으로 응답을 만드는 클래스.
from fastapi.responses import JSONResponse

# 모든 API 라우트를 묶은 라우터.
from app.api.router import api_router
# X-Service-Token 검사 의존성.
from app.core.security import require_service_token
# 서비스 계층이 던지는 예외들.
from app.service.errors import (
    # 410
    GoneError,
    # 422
    InvalidInputError,
    # 404
    NotFoundError,
    # 503
    NotReadyError,
)

# FastAPI 앱을 만든다.
app = FastAPI(
    # OpenAPI 문서에 보일 제목
    title="BizDoctor ai-service",
    # ⚠ 토큰 검사를 여기(앱 전체)에 걸지 않는다. 그러면 /health 까지 토큰을 요구해서
    # 헤더를 못 붙이는 Railway 헬스체크가 401 을 받고 컨테이너가 재시작을 반복한다.
)
# 상권·진단 라우트를 앱에 등록한다.
# 내부망 전용(AGENTS.md). /api/* 라우트만 X-Service-Token 을 검사한다 — /health 는 열어 둔다.
app.include_router(api_router, dependencies=[Depends(require_service_token)])

# F-DIA-03/04 · F-RAG-03 구현이 생기면 lifespan 에서 채운다. None 이면 POST /api/diagnosis 는 503.
app.state.predictor = None
# 정책 검색기 자리도 비워 둔다.
app.state.solution_finder = None

# 예외 종류 → HTTP 상태 코드 대응표.
_STATUS = {
    # 없음 → 404
    NotFoundError: status.HTTP_404_NOT_FOUND,
    # 만료 → 410
    GoneError: status.HTTP_410_GONE,
    # 데이터와 안 맞는 입력 → 422
    InvalidInputError: 422,
    # 준비 안 됨 → 503
    NotReadyError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


# 상태 코드를 받아, 그 코드로 응답하는 예외 핸들러 함수를 만들어 돌려준다.
def _handler(code: int):
    # 실제 핸들러: 예외 메시지를 {"detail": ...} 로 감싸 응답한다.
    async def handle(_: Request, exc: Exception) -> JSONResponse:
        # 지정된 상태 코드와 예외 메시지로 JSON 응답을 만든다.
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    # 만든 핸들러를 돌려준다.
    return handle


# 대응표의 예외마다
for exc_type, code in _STATUS.items():
    # 해당 핸들러를 앱에 등록한다.
    app.add_exception_handler(exc_type, _handler(code))


# 서버가 살아 있는지 확인하는 헬스체크 엔드포인트.
@app.get("/health", tags=["ops"])
def health() -> dict:
    # 항상 ok 를 돌려준다.
    return {"status": "ok"}
