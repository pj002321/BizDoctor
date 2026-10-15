"""F-DIA-01 매출 지수 정규화.

두 스케일이 있다 — 헷갈리면 모델 입력이 100배 틀어진다.
  - 저장·응답용 지수: 1개월차 = 100   (스펙 F-DIA-01, F-SYS-05)
  - 모델 입력 시퀀스: 1개월차 = 1.0   (train_risk_model.py: seq_raw / seq_raw[:, [0]])
"""
from __future__ import annotations

import math
from collections.abc import Sequence

INDEX_BASE = 100.0


class SalesInputError(ValueError):
    """사용자 입력 매출이 지수로 바꿀 수 없는 값일 때."""


def to_sales_index(amounts: Sequence[float], *, months: int = 3, max_amount: float | None = None) -> list[float]:
    """월매출 실금액 → 1개월차=100 지수. 금액은 이 함수 밖으로 나가지 않는다."""
    if len(amounts) != months:
        raise SalesInputError(f"월매출은 정확히 {months}개월이 필요합니다 (받은 값 {len(amounts)}개).")
    for i, a in enumerate(amounts, start=1):
        if a is None or not math.isfinite(a):
            raise SalesInputError(f"{i}개월차 매출이 숫자가 아닙니다.")
        if a < 0:
            raise SalesInputError(f"{i}개월차 매출은 0 이상이어야 합니다.")
        if max_amount is not None and a > max_amount:
            raise SalesInputError(f"{i}개월차 매출이 허용 상한을 넘습니다. 단위(원)를 확인하세요.")
    base = amounts[0]
    if base <= 0:
        raise SalesInputError("1개월차 매출이 0이면 지수를 만들 수 없습니다. 1개월차는 0보다 커야 합니다.")
    return [round(a / base * INDEX_BASE, 4) for a in amounts]


def index_to_model_sequence(index: Sequence[float]) -> list[list[float]]:
    """지수(1개월차=100) → 모델 입력 (3, 1) 시퀀스(1개월차=1.0)."""
    return [[v / INDEX_BASE] for v in index]
