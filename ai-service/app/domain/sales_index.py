# [역할] 매출 지수 변환 — 실금액 검증 후 1개월차=100 지수로, 모델 입력용으로는 1개월차=1.0 비율로 바꾼다 (F-DIA-01).
"""F-DIA-01 매출 지수 정규화.

두 스케일이 있다 — 헷갈리면 모델 입력이 100배 틀어진다.
  - 저장·응답용 지수: 1개월차 = 100   (스펙 F-DIA-01, F-SYS-05)
  - 모델 입력 시퀀스: 1개월차 = 1.0   (train_risk_model.py: seq_raw / seq_raw[:, [0]])
"""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# NaN·무한대 검사(isfinite)를 위해 가져온다.
import math
# 순서 있는 값 묶음 타입.
from collections.abc import Sequence

# 지수의 기준값 — 1개월차를 100 으로 둔다.
INDEX_BASE = 100.0


# 매출 입력이 잘못됐을 때 쓰는 예외. ValueError 를 상속해 Pydantic 이 422 로 바꿔 준다.
class SalesInputError(ValueError):
    """사용자 입력 매출이 지수로 바꿀 수 없는 값일 때."""


# 월매출 실금액 목록을 1개월차=100 지수 목록으로 바꾼다.
def to_sales_index(amounts: Sequence[float], *, months: int = 3, max_amount: float | None = None) -> list[float]:
    """월매출 실금액 → 1개월차=100 지수. 금액은 이 함수 밖으로 나가지 않는다."""
    # 개월 수가 정해진 값(기본 3)과 다르면
    if len(amounts) != months:
        # 개수가 틀렸다고 알린다.
        raise SalesInputError(f"월매출은 정확히 {months}개월이 필요합니다 (받은 값 {len(amounts)}개).")
    # 각 달 금액을 1부터 번호 매겨 하나씩 검사한다.
    for i, a in enumerate(amounts, start=1):
        # 값이 없거나 NaN·무한대이면
        if a is None or not math.isfinite(a):
            # 숫자가 아니라고 알린다(금액은 메시지에 넣지 않는다).
            raise SalesInputError(f"{i}개월차 매출이 숫자가 아닙니다.")
        # 음수이면
        if a < 0:
            # 0 이상이어야 한다고 알린다.
            raise SalesInputError(f"{i}개월차 매출은 0 이상이어야 합니다.")
        # 상한이 정해져 있고 그것을 넘으면(단위 오타 등)
        if max_amount is not None and a > max_amount:
            # 상한 초과라고 알린다.
            raise SalesInputError(f"{i}개월차 매출이 허용 상한을 넘습니다. 단위(원)를 확인하세요.")
    # 1개월차 금액을 기준값으로 잡는다.
    base = amounts[0]
    # 기준값이 0 이하이면
    if base <= 0:
        # 기준월이 0 이면 지수가 정의되지 않는다. 다른 달을 기준으로 바꾸면
        # 모델이 학습한 '1개월차 기준' 분포와 어긋나므로 거절한다.
        raise SalesInputError("1개월차 매출이 0이면 지수를 만들 수 없습니다. 1개월차는 0보다 커야 합니다.")
    # 각 달을 (금액 / 기준) × 100 으로 바꾸고 소수 4자리로 반올림한다.
    return [round(a / base * INDEX_BASE, 4) for a in amounts]


# 저장용 지수(100 기준)를 모델 입력 모양 (3, 1) 의 비율(1.0 기준)로 바꾼다.
def index_to_model_sequence(index: Sequence[float]) -> list[list[float]]:
    """지수(1개월차=100) → 모델 입력 (3, 1) 시퀀스(1개월차=1.0)."""
    # 각 값을 100 으로 나누고 [값] 형태로 감싸 LSTM 입력 모양을 만든다.
    return [[v / INDEX_BASE] for v in index]
