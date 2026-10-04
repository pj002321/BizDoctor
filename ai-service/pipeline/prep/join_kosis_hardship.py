# -*- coding: utf-8 -*-
"""
KOSIS 애로사항 데이터 파싱 → YELLOW risk_type 세부유형(업종별) 확률 산출

주의: 원본 엑셀은 '시도별(1)' 컬럼이 병합 셀이라, openpyxl로 그냥 읽으면
      각 시도의 두 번째 행부터는 빈 문자열로 나온다 (병합 셀 특성).
      반드시 forward-fill 로 시도명을 채워야 전체 시도x산업 데이터가 살아남는다.
      (이 버그 때문에 처음엔 '서울특별시'가 1행짜리 '전산업'만 잡혔었음 → 수정함)

산출물: yellow_subtype_prob.csv
  - KOSIS_산업1 별로 "원가상승_확률" 컬럼 하나만 저장
  - 원가상승_확률 = (원재료비+최저임금영향) / (원재료비+최저임금영향+동일업종경쟁심화+보증금월세)
  - generate_synthetic_timeseries.py 에서 YELLOW를 "원가_상승_부담형" vs
    "단기_매출_정체형"으로 나눌 때 이 확률로 샘플링 (기존 50:50 임의 배정을 대체)
"""
import openpyxl
import pandas as pd
import os
import sys
from pathlib import Path

# ai-service/ 를 import 경로에 넣어 app/core/config.py 를 쓴다(이 줄은 config 를 찾기 위한 것).
# 입출력 경로는 config.DATA_DIR(ai-service/data) 한 곳에서 정한다. 어디서 실행해도 같은 파일을 읽고 쓴다.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.core import config  # noqa: E402

os.chdir(config.DATA_DIR)

SRC = "raw/시도_산업중분류별_사업체운영_애로사항별_기업체수_복수응답__20260813013849.xlsx"

wb = openpyxl.load_workbook(SRC)
ws = wb["데이터"]
rows = list(ws.iter_rows(values_only=True))

# 2024년(최신) 블록 컬럼명 — 원본 시트에서 14번째(0-index)부터 12개 컬럼
COLS_2024 = [
    "기업체수", "상권쇠퇴", "동일업종경쟁심화", "원재료비", "최저임금영향",
    "보증금월세", "부채상환", "인력관리", "판로개척", "디지털기술",
    "기술개발난항", "기타",
]

records = []
last_region = None  # 병합 셀 forward-fill 용
for r in rows[2:]:  # 상단 2줄은 헤더
    if r[0] not in (None, ""):
        last_region = r[0]
    if r[1] is None:
        continue
    rec = {
        "시도": last_region,
        "산업1": r[1].strip() if isinstance(r[1], str) else r[1],
        "산업2": r[2],
    }
    for i, colname in enumerate(COLS_2024):
        rec[colname] = r[14 + i]
    records.append(rec)

df = pd.DataFrame(records)
df.to_csv("kosis_hardship_full.csv", index=False, encoding="utf-8-sig")
print("전체 파싱 결과:", df.shape, "(시도 수:", df['시도'].nunique(), ")")

# ------------------------------------------------------------------
# 서울만 추출, 산업1 단위(소계)로 YELLOW 세부유형 확률 계산
# ------------------------------------------------------------------
seoul = df[(df["시도"] == "서울특별시") & (df["산업2"] == "소계")].copy()

seoul["원가상승_스코어"] = seoul[["원재료비", "최저임금영향"]].mean(axis=1)
seoul["매출정체_스코어"] = seoul[["동일업종경쟁심화", "보증금월세"]].mean(axis=1)
seoul["원가상승_확률"] = seoul["원가상승_스코어"] / (
    seoul["원가상승_스코어"] + seoul["매출정체_스코어"]
)

out = seoul[["산업1", "원가상승_확률"]].rename(columns={"산업1": "KOSIS_산업1"})
out.to_csv("yellow_subtype_prob.csv", index=False, encoding="utf-8-sig")

print("\n=== 서울 업종별 원가상승_확률 (원가상승형 vs 매출정체형 배정 기준) ===")
print(out.to_string(index=False))