from __future__ import annotations

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.security import require_service_token
from app.service.errors import (
    GoneError,
    InvalidInputError,
    NotFoundError,
    NotReadyError,
)

app = FastAPI(
    title="BizDoctor ai-service",
)
app.include_router(api_router, dependencies=[Depends(require_service_token)])

app.state.predictor = None
app.state.solution_finder = None

_STATUS = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    GoneError: status.HTTP_410_GONE,
    InvalidInputError: 422,
    NotReadyError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _handler(code: int):
    async def handle(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    return handle


for exc_type, code in _STATUS.items():
    app.add_exception_handler(exc_type, _handler(code))


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}
