"""6개 risk_type 과 진단 등급 — 서버 쪽 단일 출처.

⚠ pipeline/ 의 네 파일(generate_synthetic_timeseries · train_risk_model ·
rag_pipeline · rag_documents)에 같은 분류가 아직 중복돼 있다. 유형을 바꾸면 그쪽도 고친다.
"""
from __future__ import annotations

from enum import StrEnum


class RiskType(StrEnum):
    정상_유지형 = "정상_유지형"
    단기_매출_정체형 = "단기_매출_정체형"
    원가_상승_부담형 = "원가_상승_부담형"
    매출_폭락형 = "매출_폭락형"
    고금리_과다채무형 = "고금리_과다채무형"
    상권_침체_붕괴형 = "상권_침체_붕괴형"


class RiskLevel(StrEnum):
    """사업장 '진단 등급'(F-DIA). 상권 '신호등'(MarketSignalLight)과 섞지 않는다(F-SYS-01)."""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class VisualTheme(StrEnum):
    green = "green"
    yellow = "yellow"
    red = "red"


RISK_TYPE_TO_LEVEL: dict[RiskType, RiskLevel] = {
    RiskType.정상_유지형: RiskLevel.GREEN,
    RiskType.단기_매출_정체형: RiskLevel.YELLOW,
    RiskType.원가_상승_부담형: RiskLevel.YELLOW,
    RiskType.매출_폭락형: RiskLevel.RED,
    RiskType.고금리_과다채무형: RiskLevel.RED,
    RiskType.상권_침체_붕괴형: RiskLevel.RED,
}


def level_of(risk_type: RiskType | str) -> RiskLevel:
    return RISK_TYPE_TO_LEVEL[RiskType(risk_type)]


def theme_of(level: RiskLevel | str) -> VisualTheme:
    return VisualTheme(RiskLevel(level).value.lower())
