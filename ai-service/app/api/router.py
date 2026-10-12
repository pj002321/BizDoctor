from fastapi import APIRouter

from app.api import diagnosis, market

api_router = APIRouter()
api_router.include_router(market.router)
api_router.include_router(diagnosis.router)
