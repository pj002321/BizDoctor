"""F-DIA-07 분포 위 위치 표시용 히스토그램."""
from __future__ import annotations

from collections.abc import Sequence


def histogram(values: Sequence[float], *, bins: int = 20, upper_clip: float | None = None) -> list[tuple[float, float, int]]:
    """등간격 히스토그램. upper_clip 이상 값은 마지막 구간에 몰아 넣는다(300% 이상치가 축을 망치지 않게)."""
    vals = [v for v in values if v is not None]
    if not vals:
        return []
    lo = min(vals)
    hi = max(vals) if upper_clip is None else min(max(vals), upper_clip)
    if hi <= lo:
        return [(lo, hi, len(vals))]
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in vals:
        i = int((min(v, hi) - lo) / width)
        counts[min(i, bins - 1)] += 1
    return [(round(lo + i * width, 4), round(lo + (i + 1) * width, 4), counts[i]) for i in range(bins)]
