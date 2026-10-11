from __future__ import annotations

from fastapi import Request

from app.service.diagnosis_service import RiskPredictor, SolutionFinder


def get_predictor(request: Request) -> RiskPredictor | None:
    """F-DIA-03/04 구현이 lifespan 에서 app.state.predictor 에 꽂힌다. 아직 없으면 None."""
    return getattr(request.app.state, "predictor", None)


def get_solution_finder(request: Request) -> SolutionFinder | None:
    return getattr(request.app.state, "solution_finder", None)
