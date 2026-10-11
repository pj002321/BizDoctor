"""F-MAP-04 개업률-폐업률 역전 구간 탐지."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Reversal:
    group: str
    quarter: str
    direction: str


def find_reversals(rows: Iterable[tuple[str, str, float | None, float | None]]) -> list[Reversal]:
    """rows: (group, quarter, open_rate, closure_rate). 분기 순서는 함수가 정렬한다.

    직전 분기와 (개업률 - 폐업률) 부호가 바뀐 분기를 역전으로 본다. 값이 같거나 비어 있으면
    부호 판단을 건너뛰고 직전 부호를 유지한다.
    """
    by_group: dict[str, list[tuple[str, float | None, float | None]]] = {}
    for g, q, o, c in rows:
        by_group.setdefault(g, []).append((q, o, c))
    out: list[Reversal] = []
    for g in sorted(by_group):
        prev_sign = 0
        for q, o, c in sorted(by_group[g]):
            if o is None or c is None or o == c:
                continue
            sign = 1 if o > c else -1
            if prev_sign and sign != prev_sign:
                out.append(Reversal(g, q, "open_over_closure" if sign > 0 else "closure_over_open"))
            prev_sign = sign
    return out
