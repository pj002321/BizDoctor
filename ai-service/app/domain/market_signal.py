"""상권 '신호등'(F-MAP) — 행정동/자치구 × 업종 단위. 사업장 '진단 등급'과 다른 개념이다(F-SYS-01)."""
from __future__ import annotations

from enum import StrEnum


class MarketSignalLight(StrEnum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


def signal_light(risk_rank: float | None, *, green_max: float, yellow_max: float) -> MarketSignalLight | None:
    """위험 순위(같은 산업 안 위험가중치 순위, 0~1) → 신호등. 값이 없으면 None(표본부족).

    위험가중치(percentile 평균) 자체를 넣지 않는다 — 평균은 0.5 근처에 몰려 기준이 걸리지 않는다.
    """
    if risk_rank is None:
        return None
    if risk_rank <= green_max:
        return MarketSignalLight.GREEN
    if risk_rank <= yellow_max:
        return MarketSignalLight.YELLOW
    return MarketSignalLight.RED


def is_small_sample(store_count: int | None, *, threshold: int) -> bool:
    """점포 수 threshold 이하 → '표본 적음' 배지. 0/33/67% 계단값 셀을 걸러 보이기 위함."""
    return store_count is None or store_count <= threshold


def top_percent(percentile: float) -> int:
    """업종 내 percentile(높을수록 위험) → '상위 N%'. 0.82 → 18."""
    p = min(max(percentile, 0.0), 1.0)
    return max(1, round((1.0 - p) * 100))
