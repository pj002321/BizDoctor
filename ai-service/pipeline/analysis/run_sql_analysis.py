# -*- coding: utf-8 -*-
"""
상권 신호등 - SQL 기반 위험 가중치 산출 및 검증

shinhan_warehouse.db 위에서 sql/risk_weights.sql 의 전처리를 실행하고,
그 결과가 기존 pandas 전처리(seoul_panel_model_ready.csv)와
일치하는지 검증한다.

핵심 검증 포인트:
  SQL 의 PERCENT_RANK()/CUME_DIST() 는 동점 처리가 pandas 의
  rank(pct=True, method='average') 와 다르다. 폐업률은 76%가 0이라
  동점이 지배적이므로, RANK() 와 동점 개수로 평균순위를 직접 계산해
  두 결과를 일치시켰다.

실행: python build_warehouse.py && python run_sql_analysis.py
"""
import sqlite3
import numpy as np
import pandas as pd
import os
import sys
from pathlib import Path

# ai-service/ 를 import 경로에 넣어 app/core/config.py 를 쓴다(이 줄은 config 를 찾기 위한 것).
# 입출력 경로는 config.DATA_DIR(ai-service/data) 한 곳에서 정한다. 어디서 실행해도 같은 파일을 읽고 쓴다.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.core import config  # noqa: E402

os.chdir(config.DATA_DIR)

DB = "shinhan_warehouse.db"
con = sqlite3.connect(DB)

# ------------------------------------------------------------------
# 1. 피처 생성 쿼리를 뷰로 등록
# ------------------------------------------------------------------
FEATURE_SQL = """
WITH panel AS (
    SELECT p.*, d."KOSIS_산업1"
    FROM seoul_panel p
    LEFT JOIN dim_industry d
           ON p."서비스_업종_코드_명" = d."서비스_업종_코드_명"
),
featured AS (
    SELECT
        "기준_년분기_코드", "행정동_코드", "행정동_코드_명",
        "서비스_업종_코드", "서비스_업종_코드_명", "KOSIS_산업1",
        "점포_수", "유사_업종_점포_수",
        "폐업_률", "개업_율", "폐업_점포_수", "프랜차이즈_점포_수",
        LEAD("폐업_률") OVER w_cell                   AS "다음분기_폐업률",
        "폐업_률" - LAG("폐업_률") OVER w_cell         AS "폐업률_변화",
        AVG("폐업_률") OVER (
            PARTITION BY "행정동_코드", "서비스_업종_코드"
            ORDER BY "기준_년분기_코드"
            ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
        )                                             AS "폐업률_2분기평균",
        "폐업_률" - "개업_율"                          AS "폐업개업_격차",
        -- 점포_수 = 일반 점포, 유사_업종_점포_수 = 일반 + 프랜차이즈(전체). 전체로 나눠야 0~1.
        CASE WHEN "유사_업종_점포_수" > 0
             THEN 1.0 * "프랜차이즈_점포_수" / "유사_업종_점포_수"
        END                                           AS "프랜차이즈_비중",
        (CAST(RANK() OVER w_rank AS REAL)
            + (COUNT(*) OVER w_tie - 1) / 2.0)
        / COUNT(*) OVER w_part                        AS "폐업률_업종내_percentile"
    FROM panel
    WINDOW
        w_cell AS (PARTITION BY "행정동_코드", "서비스_업종_코드"
                   ORDER BY "기준_년분기_코드"),
        w_rank AS (PARTITION BY "기준_년분기_코드", "서비스_업종_코드"
                   ORDER BY "폐업_률"),
        w_tie  AS (PARTITION BY "기준_년분기_코드", "서비스_업종_코드", "폐업_률"),
        w_part AS (PARTITION BY "기준_년분기_코드", "서비스_업종_코드")
)
SELECT * FROM featured WHERE "다음분기_폐업률" IS NOT NULL
"""

con.execute("DROP VIEW IF EXISTS v_featured")
con.execute(f"CREATE VIEW v_featured AS {FEATURE_SQL}")
print("뷰 생성: v_featured")

sql_df = pd.read_sql_query("SELECT * FROM v_featured", con)
print(f"SQL 산출 행 수: {len(sql_df):,}")

# ------------------------------------------------------------------
# 2. pandas 전처리 결과와 대조
# ------------------------------------------------------------------
print("\n" + "=" * 68)
print("검증 - pandas 전처리 결과와 일치하는가")
print("=" * 68)

pd_df = pd.read_csv("seoul_panel_model_ready.csv")
KEY = ["기준_년분기_코드", "행정동_코드", "서비스_업종_코드"]
print(f"  pandas 행 수 : {len(pd_df):,}")
print(f"  SQL    행 수 : {len(sql_df):,}")
print(f"  행 수 일치   : {'예' if len(pd_df) == len(sql_df) else '아니오'}")

merged = pd_df.merge(sql_df, on=KEY, suffixes=("_pd", "_sql"))
print(f"  키 조인 성공 : {len(merged):,}행")

CHECK = ["다음분기_폐업률", "폐업률_변화", "폐업률_2분기평균",
         "폐업개업_격차", "프랜차이즈_비중", "폐업률_업종내_percentile"]
print()
all_ok = True
for col in CHECK:
    a, b = merged[f"{col}_pd"], merged[f"{col}_sql"]
    both_na = a.isna() & b.isna()
    diff = (a - b).abs()
    max_diff = diff[~both_na].max()
    ok = bool(np.nan_to_num(max_diff, nan=0.0) < 1e-9)
    all_ok &= ok
    print(f"  {'[일치]' if ok else '[불일치]'} {col:<24} 최대오차 {max_diff:.2e}")

print("\n  →", "모든 피처가 pandas 결과와 일치합니다." if all_ok
      else "일부 피처가 불일치합니다. 쿼리를 확인하세요.")

# ------------------------------------------------------------------
# 3. 지역 x 업종별 위험 가중치 (자소서의 "연체 가중치 산출")
# ------------------------------------------------------------------
print("\n" + "=" * 68)
print("지역 x 업종별 위험 가중치 - 상위 15")
print("=" * 68)
# 행정동은 코드로 묶는다 — 이름으로 묶으면 신사동(강남구·관악구)이 한 행으로 합쳐진다.
# 연점포수는 전체 점포(유사_업종_점포_수) 합계다. 점포_수는 프랜차이즈를 뺀 일반 점포.
WEIGHTS_SQL = """
    SELECT
        "행정동_코드"                             AS 행정동코드,
        MIN("행정동_코드_명")                     AS 행정동,
        "KOSIS_산업1"                             AS 산업대분류,
        COUNT(*)                                  AS 관측분기수,
        SUM("유사_업종_점포_수")                  AS 연점포수,
        ROUND(AVG("폐업_률"), 2)                  AS 평균폐업률,
        ROUND(AVG("폐업률_업종내_percentile"), 4) AS 위험가중치,
        ROUND(AVG("폐업개업_격차"), 2)             AS 폐업개업격차
    FROM v_featured
    GROUP BY "행정동_코드", "KOSIS_산업1"
    HAVING COUNT(*) >= :min_obs AND SUM("유사_업종_점포_수") >= :min_stores
    ORDER BY 위험가중치 DESC
"""
weights_full = pd.read_sql_query(WEIGHTS_SQL, con, params={
    "min_obs": config.REGION_RISK_MIN_OBS,        # 관측 8건 이상
    "min_stores": config.REGION_RISK_MIN_STORES,  # 전체 점포 합계 100 이상
})
print(weights_full.head(15).to_string(index=False))
weights_full.to_csv("risk_weights_by_region_industry.csv",
                    index=False, encoding="utf-8-sig")
print(f"\n저장: risk_weights_by_region_industry.csv ({len(weights_full):,}행)")

# ------------------------------------------------------------------
# 4. KOSIS 조인 — 폐업 위험과 원가상승 부담
# ------------------------------------------------------------------
print("\n" + "=" * 68)
print("산업대분류별 폐업률과 원가상승 확률 (KOSIS 조인)")
print("=" * 68)
print(pd.read_sql_query("""
    WITH seoul_hardship AS (
        SELECT "산업1" AS "KOSIS_산업1",
               ("원재료비" + "최저임금영향") / 2.0      AS 원가상승_스코어,
               ("동일업종경쟁심화" + "보증금월세") / 2.0 AS 매출정체_스코어
        FROM kosis_hardship
        WHERE "시도" = '서울특별시' AND "산업2" = '소계'
    )
    SELECT f."KOSIS_산업1" AS 산업대분류,
           ROUND(AVG(f."폐업_률"), 2) AS 평균폐업률,
           ROUND(h.원가상승_스코어
                 / (h.원가상승_스코어 + h.매출정체_스코어), 3) AS 원가상승_확률
    FROM v_featured f
    JOIN seoul_hardship h ON f."KOSIS_산업1" = h."KOSIS_산업1"
    GROUP BY f."KOSIS_산업1"
    ORDER BY 평균폐업률 DESC
""", con).to_string(index=False))

# ------------------------------------------------------------------
# 5. 신보 부실사유 분포
# ------------------------------------------------------------------
print("\n" + "=" * 68)
print("신용보증기금 부실사유 분포 (RED 세부유형 배분 근거)")
print("=" * 68)
print(pd.read_sql_query("""
    SELECT "부실사유코드" AS 부실사유, COUNT(*) AS 건수,
           ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS 비중_pct
    FROM sgf_default
    GROUP BY "부실사유코드"
    ORDER BY 건수 DESC
    LIMIT 8
""", con).to_string(index=False))

con.commit()
con.close()
