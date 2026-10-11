# [역할] 위험 유형 표 — 6개 risk_type → 진단 등급(GREEN/YELLOW/RED) → visual_theme 매핑의 단일 출처.
"""6개 risk_type 과 진단 등급 — 서버 쪽 단일 출처.

⚠ pipeline/ 의 네 파일(generate_synthetic_timeseries · train_risk_model ·
rag_pipeline · rag_documents)에 같은 분류가 아직 중복돼 있다. 유형을 바꾸면 그쪽도 고친다.
"""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 값이 문자열로 직렬화되는 열거형.
from enum import StrEnum


# 모델이 예측하는 6가지 위기 원인 유형.
class RiskType(StrEnum):
    # GREEN — 정상
    정상_유지형 = "정상_유지형"
    # YELLOW — 매출이 잠시 정체
    단기_매출_정체형 = "단기_매출_정체형"
    # YELLOW — 원가 부담 증가
    원가_상승_부담형 = "원가_상승_부담형"
    # RED — 매출 급감
    매출_폭락형 = "매출_폭락형"
    # RED — 대출 상환 부담
    고금리_과다채무형 = "고금리_과다채무형"
    # RED — 상권 자체 쇠퇴
    상권_침체_붕괴형 = "상권_침체_붕괴형"


# 사업장 진단 등급 3단계.
class RiskLevel(StrEnum):
    """사업장 '진단 등급'(F-DIA). 상권 '신호등'(MarketSignalLight)과 섞지 않는다(F-SYS-01)."""

    # 안정
    GREEN = "GREEN"
    # 주의
    YELLOW = "YELLOW"
    # 위험
    RED = "RED"


# 프론트 화면 테마 값(스펙의 visual_theme: "red" 등 소문자).
class VisualTheme(StrEnum):
    # 초록 테마
    green = "green"
    # 노랑 테마
    yellow = "yellow"
    # 빨강 테마
    red = "red"


# 유형 → 등급 대응표. 등급은 이 표로만 정한다.
RISK_TYPE_TO_LEVEL: dict[RiskType, RiskLevel] = {
    # 정상 → GREEN
    RiskType.정상_유지형: RiskLevel.GREEN,
    # 단기 정체 → YELLOW
    RiskType.단기_매출_정체형: RiskLevel.YELLOW,
    # 원가 상승 → YELLOW
    RiskType.원가_상승_부담형: RiskLevel.YELLOW,
    # 매출 폭락 → RED
    RiskType.매출_폭락형: RiskLevel.RED,
    # 고금리 채무 → RED
    RiskType.고금리_과다채무형: RiskLevel.RED,
    # 상권 침체 → RED
    RiskType.상권_침체_붕괴형: RiskLevel.RED,
}


# 유형(문자열도 가능)을 받아 진단 등급을 돌려준다.
def level_of(risk_type: RiskType | str) -> RiskLevel:
    # 문자열이면 RiskType 으로 바꾼 뒤(없는 유형이면 ValueError) 표에서 찾는다.
    return RISK_TYPE_TO_LEVEL[RiskType(risk_type)]


# 등급을 받아 화면 테마를 돌려준다.
def theme_of(level: RiskLevel | str) -> VisualTheme:
    # 'RED' → 'red' 처럼 소문자로 바꿔 VisualTheme 으로 만든다.
    return VisualTheme(RiskLevel(level).value.lower())
