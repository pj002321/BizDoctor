# [역할] 라우터 묶음 — market·diagnosis 라우터를 하나로 모아 main.py 에 등록한다.
# FastAPI 의 라우터 클래스를 가져온다.
from fastapi import APIRouter

# 상권 조회·진단 라우트가 정의된 두 모듈을 가져온다.
from app.api import diagnosis, market

# 모든 하위 라우터를 담을 최상위 라우터를 만든다.
api_router = APIRouter()
# 상권 조회 라우트(/api/market/*)를 붙인다.
api_router.include_router(market.router)
# 진단 라우트(/api/diagnosis*)를 붙인다.
api_router.include_router(diagnosis.router)
