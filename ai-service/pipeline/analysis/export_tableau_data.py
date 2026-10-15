# -*- coding: utf-8 -*-
"""
상권 신호등 - Tableau 시각화용 데이터 추출

SQL 웨어하우스(shinhan_warehouse.db)의 v_featured 뷰에서
Tableau가 바로 연결할 수 있는 형태로 내보낸다.

설계 원칙:
  - Tableau는 조인보다 "넓은 단일 테이블"이 다루기 쉬우므로 비정규화한다.
  - 분기 코드(20231)를 실제 날짜로 변환해야 Tableau가 시간축으로 인식한다.
  - 지도 시각화를 위해 행정동 코드 앞 5자리로 자치구를 복원한다.
    (Tableau 내장 지오코딩은 한국 시/군/구까지 인식, 행정동은 미지원)

산출물 (tableau/ 폴더):
  tableau_panel.csv          상권 패널 팩트 테이블 (387,266행)
  tableau_region_summary.csv 자치구 x 산업 요약 (지도용)
  tableau_model_results.csv  모델 예측 결과 (6,000행)

실행: python build_warehouse.py && python run_sql_analysis.py && python export_tableau_data.py
"""
import os
import sys
import sqlite3
import pandas as pd
from pathlib import Path

# ai-service/ 를 import 경로에 넣어 app/core/config.py 를 쓴다(이 줄은 config 를 찾기 위한 것).
# 입출력 경로는 config.DATA_DIR(ai-service/data) 한 곳에서 정한다. 어디서 실행해도 같은 파일을 읽고 쓴다.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.core import config  # noqa: E402

os.chdir(config.DATA_DIR)

OUT_DIR = "tableau"
os.makedirs(OUT_DIR, exist_ok=True)

con = sqlite3.connect("shinhan_warehouse.db")

# v_featured 뷰가 없으면 run_sql_analysis.py 를 먼저 돌려야 한다
views = pd.read_sql_query(
    "SELECT name FROM sqlite_master WHERE type='view' AND name='v_featured'", con)
if views.empty:
    raise SystemExit("v_featured 뷰가 없습니다. run_sql_analysis.py 를 먼저 실행하세요.")

# ------------------------------------------------------------------
# 1. 팩트 테이블 — KOSIS 원가상승 확률까지 비정규화해서 붙임
# ------------------------------------------------------------------
panel = pd.read_sql_query("""
    WITH seoul_hardship AS (
        SELECT "산업1" AS "KOSIS_산업1",
               ("원재료비" + "최저임금영향") / 2.0                    AS cost_score,
               ("동일업종경쟁심화" + "보증금월세") / 2.0               AS stall_score
        FROM kosis_hardship
        WHERE "시도" = '서울특별시' AND "산업2" = '소계'
    )
    SELECT
        f."기준_년분기_코드"                                          AS 분기코드,
        f."행정동_코드"                                               AS 행정동코드,
        f."행정동_코드_명"                                            AS 행정동,
        f."서비스_업종_코드_명"                                       AS 업종,
        f."KOSIS_산업1"                                               AS 산업대분류,
        -- 점포수 = 전체 점포(일반 + 프랜차이즈). 점포_수는 프랜차이즈를 뺀 일반 점포라
        -- 이걸 분모로 쓰면 편의점 실질폐업률이 3.3% → 12.3% 로 부풀려진다.
        f."유사_업종_점포_수"                                         AS 점포수,
        f."폐업_점포_수"                                              AS 폐업점포수,
        f."폐업_률"                                                   AS 폐업률,
        f."개업_율"                                                   AS 개업률,
        f."폐업개업_격차"                                             AS 폐업개업격차,
        f."폐업률_변화"                                               AS 폐업률변화,
        f."폐업률_업종내_percentile"                                  AS 위험가중치,
        f."프랜차이즈_비중"                                           AS 프랜차이즈비중,
        f."다음분기_폐업률"                                           AS 다음분기폐업률,
        ROUND(h.cost_score / (h.cost_score + h.stall_score), 4)       AS 원가상승확률
    FROM v_featured f
    LEFT JOIN seoul_hardship h ON f."KOSIS_산업1" = h."KOSIS_산업1"
""", con)

# 자치구 복원 + 분기를 날짜로 변환 (Tableau 시간축 인식용)
panel["자치구"] = panel["행정동코드"].astype(str).str[:5].map(config.GU_CODE)
panel["연도"] = panel["분기코드"].astype(str).str[:4].astype(int)
panel["분기"] = panel["분기코드"].astype(str).str[4].astype(int)
panel["분기시작일"] = pd.to_datetime(
    panel["연도"].astype(str) + "-" + ((panel["분기"] - 1) * 3 + 1).astype(str) + "-01"
)
panel["분기표기"] = panel["연도"].astype(str) + " Q" + panel["분기"].astype(str)

# 위험등급 — 대시보드 색상 구분용 (신호등 3색)
panel["위험등급"] = pd.cut(
    panel["위험가중치"], bins=[-0.01, config.SIGNAL_LIGHT_GREEN_MAX, config.SIGNAL_LIGHT_YELLOW_MAX, 1.01],
    labels=["GREEN 안정", "YELLOW 주의", "RED 위험"]
)

COLS = ["분기시작일", "분기표기", "연도", "분기", "자치구", "행정동", "업종", "산업대분류",
        "점포수", "폐업점포수", "폐업률", "개업률", "폐업개업격차", "폐업률변화",
        "위험가중치", "위험등급", "프랜차이즈비중", "원가상승확률", "다음분기폐업률"]
panel[COLS].to_csv(f"{OUT_DIR}/tableau_panel.csv", index=False, encoding="utf-8-sig")
print(f"  tableau_panel.csv           {len(panel):>7,}행  자치구 {panel['자치구'].nunique()}개")

# ------------------------------------------------------------------
# 2. 자치구 x 산업 요약 — 지도/히트맵용 (작고 빠름)
# ------------------------------------------------------------------
summary = (
    panel.groupby(["자치구", "산업대분류"], observed=True)
    .agg(점포수=("점포수", "sum"),
         폐업점포수=("폐업점포수", "sum"),
         평균폐업률=("폐업률", "mean"),
         평균개업률=("개업률", "mean"),
         위험가중치=("위험가중치", "mean"),
         관측수=("폐업률", "size"))
    .reset_index()
)
summary.insert(0, "시도", "서울특별시")   # Tableau 지오코딩이 자치구를 인식하려면 상위 지역이 필요
summary["실질폐업률"] = (summary["폐업점포수"] / summary["점포수"] * 100).round(3)
summary[["평균폐업률", "평균개업률", "위험가중치"]] = \
    summary[["평균폐업률", "평균개업률", "위험가중치"]].round(4)
summary.to_csv(f"{OUT_DIR}/tableau_region_summary.csv", index=False, encoding="utf-8-sig")
print(f"  tableau_region_summary.csv  {len(summary):>7,}행  (지도용)")

# ------------------------------------------------------------------
# 3. 모델 예측 결과 — 성능 대시보드용
# ------------------------------------------------------------------
pred = pd.read_csv("model_predictions_sample.csv")
pred = pred.rename(columns={
    "행정동_코드_명": "행정동", "서비스_업종_코드_명": "업종",
    "risk_type": "실제유형", "risk_level": "실제등급",
    "예측_risk_type": "예측유형", "예측_risk_level": "예측등급",
    "score": "위험점수",
})
pred["등급정답"] = (pred["실제등급"] == pred["예측등급"]).map({True: "정답", False: "오답"})
pred["유형정답"] = pred["정답여부"].map({True: "정답", False: "오답"})
# 자치구는 행정동 코드 앞 5자리로 정한다. 이름으로 찾으면 신사동이 전부 한 자치구로 붙는다.
if "행정동_코드" in pred.columns:
    pred["자치구"] = pred["행정동_코드"].astype(str).str[:5].map(config.GU_CODE)
else:  # train_risk_model.py 를 다시 돌리기 전의 예전 파일
    print("  [경고] model_predictions_sample.csv 에 행정동_코드가 없어 이름으로 자치구를 찾습니다(신사동 부정확).")
    pred["자치구"] = pred["행정동"].map(
        panel.drop_duplicates("행정동").set_index("행정동")["자치구"])
pred[["company_id", "자치구", "행정동", "업종", "실제등급", "예측등급",
      "실제유형", "예측유형", "등급정답", "유형정답", "위험점수"]].to_csv(
    f"{OUT_DIR}/tableau_model_results.csv", index=False, encoding="utf-8-sig")
print(f"  tableau_model_results.csv   {len(pred):>7,}행")

con.close()
print(f"\n완료 - {OUT_DIR}/ 폴더의 3개 파일을 Tableau에서 열면 됩니다.")
