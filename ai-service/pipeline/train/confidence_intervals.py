# -*- coding: utf-8 -*-
"""
상권 신호등 - 성능 지표의 95% 신뢰구간

지금까지의 지표(RED 재현율 93.3% 등)는 테스트셋 한 번에서 나온 점 추정치다.
"그 숫자를 얼마나 믿을 수 있나"에 답하려면 구간이 필요하다.

재현율·정밀도는 모두 비율(proportion)이므로 Wilson score interval 을 쓴다.
  - 정규근사(±1.96·√(p(1-p)/n))는 p가 0이나 1에 가까울 때 구간이 음수가 되거나
    폭이 0이 되는 문제가 있다.
  - Wilson 은 그 경우에도 타당한 구간을 준다. 상권_침체_붕괴형처럼
    성공 0건인 클래스에서 특히 중요하다.

실행: python confidence_intervals.py
"""
import math
import pandas as pd
import os
from pathlib import Path

# 입출력 경로는 전부 ai-service/data/ 기준이다. 어디서 실행해도 같은 파일을 읽고 쓴다.
os.chdir(Path(__file__).resolve().parents[2] / "data")

Z = 1.959963985  # 95%


def wilson(k, n, z=Z):
    """성공 k회 / 시행 n회 의 Wilson score 95% 신뢰구간"""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return (max(0.0, center - half), min(1.0, center + half))


def row(name, k, n):
    lo, hi = wilson(k, n)
    p = k / n if n else float("nan")
    return {
        "지표": name, "성공/시행": f"{k}/{n}",
        "추정치": f"{p*100:.1f}%",
        "95% 신뢰구간": f"{lo*100:.1f}% ~ {hi*100:.1f}%",
        "구간폭": f"{(hi-lo)*100:.1f}%p",
    }


pred = pd.read_csv("model_predictions_sample.csv")
lv_t, lv_p = pred["risk_level"], pred["예측_risk_level"]
ty_t, ty_p = pred["risk_type"], pred["예측_risk_type"]

rows = []
print("=" * 78)
print("등급별 재현율 (Recall) — 실제 X 중 X로 맞힌 비율")
print("=" * 78)
for L in ["GREEN", "YELLOW", "RED"]:
    m = lv_t == L
    rows.append(row(f"{L} 재현율", int((lv_p[m] == L).sum()), int(m.sum())))
print(pd.DataFrame(rows).to_string(index=False))

rows2 = []
print("\n" + "=" * 78)
print("등급별 정밀도 (Precision) — X로 예측한 것 중 실제 X인 비율")
print("=" * 78)
for L in ["GREEN", "YELLOW", "RED"]:
    m = lv_p == L
    if m.sum() == 0:
        continue
    rows2.append(row(f"{L} 정밀도", int((lv_t[m] == L).sum()), int(m.sum())))
print(pd.DataFrame(rows2).to_string(index=False))

rows3 = []
print("\n" + "=" * 78)
print("유형별 재현율 — 표본이 적을수록 구간이 넓어진다")
print("=" * 78)
for t in sorted(ty_t.unique()):
    m = ty_t == t
    rows3.append(row(t, int((ty_p[m] == t).sum()), int(m.sum())))
print(pd.DataFrame(rows3).sort_values("지표").to_string(index=False))

print("\n" + "=" * 78)
print("읽는 법")
print("=" * 78)
print("  · 구간이 좁다  = 표본이 충분해 숫자를 믿을 만하다")
print("  · 구간이 넓다  = 표본이 적어 우연일 수 있다")
print("  · 상권_침체_붕괴형은 성공 0건이지만 구간 상한이 0%가 아니다.")
print("    표본 74건으로는 '진짜 0%'인지 '운 나쁘게 0건'인지 구분할 수 없다는 뜻.")
