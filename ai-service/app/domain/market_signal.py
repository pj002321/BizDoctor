# [역할] 상권 신호등 — 위험가중치→GREEN/YELLOW/RED, '표본 적음' 판정, '상위 N%' 계산 (F-MAP).
"""상권 '신호등'(F-MAP) — 행정동/자치구 × 업종 단위. 사업장 '진단 등급'과 다른 개념이다(F-SYS-01)."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 값이 문자열로 직렬화되는 열거형.
from enum import StrEnum


# 상권 신호등 색 3가지. 사업장 진단 등급(RiskLevel)과 일부러 다른 타입으로 둔다.
class MarketSignalLight(StrEnum):
    # 같은 산업 안 하위 60%
    GREEN = "GREEN"
    # 그다음 25%
    YELLOW = "YELLOW"
    # 상위 15%
    RED = "RED"


# 위험 순위를 신호등 색으로 바꾼다. 기준값은 호출하는 쪽(config)에서 넘긴다.
def signal_light(risk_rank: float | None, *, green_max: float, yellow_max: float) -> MarketSignalLight | None:
    """위험 순위(같은 산업 안 위험가중치 순위, 0~1) → 신호등. 값이 없으면 None(표본부족).

    위험가중치(percentile 평균) 자체를 넣지 않는다 — 평균은 0.5 근처에 몰려 기준이 걸리지 않는다.
    """
    # 순위가 없으면
    if risk_rank is None:
        # 색을 정하지 않는다(표본부족).
        return None
    # GREEN 기준 이하이면
    if risk_rank <= green_max:
        # 초록
        return MarketSignalLight.GREEN
    # YELLOW 기준 이하이면
    if risk_rank <= yellow_max:
        # 노랑
        return MarketSignalLight.YELLOW
    # 그 외에는 빨강
    return MarketSignalLight.RED


# 점포 수가 적어 폐업률이 들쭉날쭉한 셀인지 판정한다.
def is_small_sample(store_count: int | None, *, threshold: int) -> bool:
    """점포 수 threshold 이하 → '표본 적음' 배지. 0/33/67% 계단값 셀을 걸러 보이기 위함."""
    # 점포 수를 모르거나 기준 이하이면 True.
    return store_count is None or store_count <= threshold


# percentile 을 '상위 N%' 의 N 으로 바꾼다.
def top_percent(percentile: float) -> int:
    """업종 내 percentile(높을수록 위험) → '상위 N%'. 0.82 → 18."""
    # 값을 0~1 범위로 잘라 둔다.
    p = min(max(percentile, 0.0), 1.0)
    # (1 - p) × 100 을 반올림하고, '상위 0%' 가 나오지 않게 최소 1 로 맞춘다.
    return max(1, round((1.0 - p) * 100))
