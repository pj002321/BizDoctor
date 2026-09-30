# -*- coding: utf-8 -*-
"""
상권 신호등 - SQL 웨어하우스 구축

원천 데이터 3종을 SQLite 데이터베이스(shinhan_warehouse.db)에 적재한다.
이후 sql/risk_weights.sql 이 이 DB 위에서 지역·업종별 위험 가중치를 산출한다.

  seoul_panel    서울시 상권분석 점포-행정동 패널 (2023~2025, 423,454행)
  dim_industry   서비스업종(100) → KOSIS 산업중분류(12) 매핑 차원 테이블
  kosis_hardship 시도x산업별 사업체 운영 애로사항
  sgf_default    신용보증기금 채권관리 부실사유

실행: python build_warehouse.py
"""
import sqlite3
import pandas as pd
import os
from pathlib import Path

# 입출력 경로는 전부 ai-service/data/ 기준이다. 어디서 실행해도 같은 파일을 읽고 쓴다.
os.chdir(Path(__file__).resolve().parents[2] / "data")

DB = "shinhan_warehouse.db"

con = sqlite3.connect(DB)
cur = con.cursor()
print(f"SQLite {sqlite3.sqlite_version} → {DB}")

# ------------------------------------------------------------------
# 1. 서울 상권 패널 (원천 parquet)
# ------------------------------------------------------------------
panel = pd.read_parquet("seoul_panel_raw.parquet")
panel.to_sql("seoul_panel", con, if_exists="replace", index=False)
print(f"  seoul_panel      {len(panel):>8,}행")

# ------------------------------------------------------------------
# 2. 업종 매핑 차원 테이블
#    preprocess_seoul_panel.py 가 만든 매핑 결과에서 고유쌍만 추출.
#    (매핑 딕셔너리를 중복 정의하지 않기 위해 산출물에서 역으로 뽑는다)
# ------------------------------------------------------------------
dim = (
    pd.read_csv("seoul_panel_model_ready.csv",
                usecols=["서비스_업종_코드_명", "KOSIS_산업1"])
    .drop_duplicates()
    .dropna()
    .sort_values("서비스_업종_코드_명")
)
dim.to_sql("dim_industry", con, if_exists="replace", index=False)
print(f"  dim_industry     {len(dim):>8,}행  (업종 → KOSIS 산업중분류)")

# ------------------------------------------------------------------
# 3. KOSIS 애로사항
# ------------------------------------------------------------------
kosis = pd.read_csv("kosis_hardship_full.csv", encoding="utf-8-sig")
kosis.to_sql("kosis_hardship", con, if_exists="replace", index=False)
print(f"  kosis_hardship   {len(kosis):>8,}행")

# ------------------------------------------------------------------
# 4. 신용보증기금 부실사유
#    (컬럼명이 정상 디코딩되는 BOM 파일을 사용)
# ------------------------------------------------------------------
sgf = pd.read_csv("raw/sgf176_utf8_bom.csv", encoding="utf-8-sig")
sgf.to_sql("sgf_default", con, if_exists="replace", index=False)
print(f"  sgf_default      {len(sgf):>8,}행")

# ------------------------------------------------------------------
# 5. 인덱스 — 윈도우 함수의 PARTITION BY 키 기준
# ------------------------------------------------------------------
INDEXES = [
    ('idx_panel_cell',    'seoul_panel("행정동_코드","서비스_업종_코드","기준_년분기_코드")'),
    ('idx_panel_quarter', 'seoul_panel("기준_년분기_코드","서비스_업종_코드")'),
    ('idx_dim_name',      'dim_industry("서비스_업종_코드_명")'),
]
for name, target in INDEXES:
    cur.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {target}")
    print(f"  index            {name}")

con.commit()

size = cur.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()").fetchone()[0]
print(f"\n완료 — {DB} ({size/1024/1024:.1f} MB)")
con.close()
