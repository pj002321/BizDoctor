# [역할] API 의존성 — app.state 에 꽂힌 진단 모델(predictor)·정책 검색기(solution_finder)를 라우트에 넘겨준다.
# 타입 힌트를 문자열로 늦게 평가해 순환 import·전방 참조 문제를 피한다.
from __future__ import annotations

# 현재 요청 객체 — 여기서 app.state 에 접근한다.
from fastapi import Request

# 모델·검색기가 따라야 할 인터페이스(Protocol) 타입을 가져온다.
from app.service.diagnosis_service import RiskPredictor, SolutionFinder


# 라우트에서 Depends(get_predictor) 로 진단 모델을 주입받는 함수.
def get_predictor(request: Request) -> RiskPredictor | None:
    """F-DIA-03/04 구현이 lifespan 에서 app.state.predictor 에 꽂힌다. 아직 없으면 None."""
    # app.state 에 predictor 가 있으면 그것을, 없으면 None 을 돌려준다.
    return getattr(request.app.state, "predictor", None)


# 라우트에서 Depends(get_solution_finder) 로 정책 검색기를 주입받는 함수.
def get_solution_finder(request: Request) -> SolutionFinder | None:
    # app.state 에 solution_finder 가 있으면 그것을, 없으면 None 을 돌려준다.
    return getattr(request.app.state, "solution_finder", None)
