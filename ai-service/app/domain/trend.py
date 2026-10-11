# [역할] 추이 분석 — 분기별 개업률·폐업률 부호가 바뀌는 '역전 구간'을 찾는다 (F-MAP-04).
"""F-MAP-04 개업률-폐업률 역전 구간 탐지."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 반복 가능한 값 묶음 타입.
from collections.abc import Iterable
# 값만 담는 간단한 클래스를 만드는 데코레이터.
from dataclasses import dataclass


# 역전 한 건을 나타내는 불변(frozen) 데이터 클래스.
@dataclass(frozen=True)
class Reversal:
    # 산업대분류 이름
    group: str
    # 역전이 일어난 분기
    quarter: str
    # 역전 방향
    direction: str  # "closure_over_open" | "open_over_closure"


# (그룹, 분기, 개업률, 폐업률) 행들에서 역전 분기를 찾아 목록으로 돌려준다.
def find_reversals(rows: Iterable[tuple[str, str, float | None, float | None]]) -> list[Reversal]:
    """rows: (group, quarter, open_rate, closure_rate). 분기 순서는 함수가 정렬한다.

    직전 분기와 (개업률 - 폐업률) 부호가 바뀐 분기를 역전으로 본다. 값이 같거나 비어 있으면
    부호 판단을 건너뛰고 직전 부호를 유지한다.
    """
    # 그룹별로 (분기, 개업률, 폐업률)을 모아 둘 딕셔너리.
    by_group: dict[str, list[tuple[str, float | None, float | None]]] = {}
    # 입력 행을 하나씩 꺼내
    for g, q, o, c in rows:
        # 해당 그룹 목록에 추가한다(없으면 빈 목록부터 만든다).
        by_group.setdefault(g, []).append((q, o, c))
    # 결과를 담을 목록.
    out: list[Reversal] = []
    # 그룹 이름 순서대로 돌면서
    for g in sorted(by_group):
        # 직전 분기의 부호. 0 은 '아직 없음'.
        prev_sign = 0
        # 분기 순서대로 정렬해서 본다.
        for q, o, c in sorted(by_group[g]):
            # 값이 비었거나 개업률=폐업률이면 부호를 정할 수 없으니
            if o is None or c is None or o == c:
                # 이 분기는 건너뛴다.
                continue
            # 개업률이 크면 +1, 폐업률이 크면 -1.
            sign = 1 if o > c else -1
            # 직전 부호가 있고 지금과 다르면 역전이다.
            if prev_sign and sign != prev_sign:
                # 바뀐 방향을 붙여 결과에 추가한다.
                out.append(Reversal(g, q, "open_over_closure" if sign > 0 else "closure_over_open"))
            # 현재 부호를 다음 비교용으로 기억한다.
            prev_sign = sign
    # 찾은 역전 목록을 돌려준다.
    return out
