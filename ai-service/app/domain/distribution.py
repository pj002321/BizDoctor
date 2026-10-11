# [역할] 분포 계산 — F-DIA-07 '상권 대비 위치'용 폐업률 히스토그램을 만든다(이상치는 마지막 구간으로).
"""F-DIA-07 분포 위 위치 표시용 히스토그램."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 리스트·튜플 등 '순서 있는 값 묶음'을 뜻하는 타입.
from collections.abc import Sequence


# values 를 bins 개의 같은 폭 구간으로 나눠 (하한, 상한, 개수) 목록을 돌려준다.
def histogram(values: Sequence[float], *, bins: int = 20, upper_clip: float | None = None) -> list[tuple[float, float, int]]:
    """등간격 히스토그램. upper_clip 이상 값은 마지막 구간에 몰아 넣는다(300% 이상치가 축을 망치지 않게)."""
    # None 값을 빼고 실제 숫자만 남긴다.
    vals = [v for v in values if v is not None]
    # 남은 값이 하나도 없으면
    if not vals:
        # 빈 히스토그램을 돌려준다.
        return []
    # 가장 작은 값을 히스토그램 시작점으로 쓴다.
    lo = min(vals)
    # 끝점: 상한 제한이 없으면 최댓값, 있으면 최댓값과 상한 중 작은 쪽.
    hi = max(vals) if upper_clip is None else min(max(vals), upper_clip)
    # 모든 값이 같아서 폭을 만들 수 없으면
    if hi <= lo:
        # 구간 하나에 전부 담아 돌려준다.
        return [(lo, hi, len(vals))]
    # 구간 하나의 폭을 계산한다.
    width = (hi - lo) / bins
    # 구간별 개수를 0 으로 초기화한다.
    counts = [0] * bins
    # 값을 하나씩 보면서
    for v in vals:
        # 상한을 넘는 값은 상한으로 눌러서 몇 번째 구간인지 구한다.
        i = int((min(v, hi) - lo) / width)
        # 정확히 상한인 값은 인덱스가 bins 가 되므로 마지막 구간으로 맞춰 개수를 올린다.
        counts[min(i, bins - 1)] += 1
    # 각 구간의 (하한, 상한, 개수)를 소수 4자리로 반올림해 돌려준다.
    return [(round(lo + i * width, 4), round(lo + (i + 1) * width, 4), counts[i]) for i in range(bins)]
