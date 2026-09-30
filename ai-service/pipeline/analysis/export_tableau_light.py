# -*- coding: utf-8 -*-
"""
Tableau 경량 추출 — 59MB 팩트 테이블 없이도 대시보드를 만들 수 있게
미리 집계한 작은 파일을 만든다. (Tableau 로딩 속도 확보용)

산출물:
  tableau/tableau_quarterly.csv   분기 x 산업대분류 추이 (추이 차트용)
  tableau/tableau_industry.csv    업종별 폐업률 순위 (막대 차트용)

실행: python export_tableau_light.py
"""
import pandas as pd
import os
from pathlib import Path

# 입출력 경로는 전부 ai-service/data/ 기준이다. 어디서 실행해도 같은 파일을 읽고 쓴다.
os.chdir(Path(__file__).resolve().parents[2] / "data")

SRC = "tableau/tableau_panel.csv"
panel = pd.read_csv(SRC)

# ------------------------------------------------------------------
# 1. 분기 x 산업대분류 추이
# ------------------------------------------------------------------
q = (panel.groupby(["분기시작일", "분기표기", "산업대분류"], as_index=False)
          .agg(점포수=("점포수", "sum"),
               폐업점포수=("폐업점포수", "sum"),
               평균폐업률=("폐업률", "mean"),
               평균개업률=("개업률", "mean")))
q["실질폐업률"] = (q["폐업점포수"] / q["점포수"] * 100).round(3)
q[["평균폐업률", "평균개업률"]] = q[["평균폐업률", "평균개업률"]].round(3)
q.to_csv("tableau/tableau_quarterly.csv", index=False, encoding="utf-8-sig")
print(f"  tableau_quarterly.csv  {len(q):>5,}행  (분기 x 산업)")

# 서울 전체 합계도 한 줄로 넣어 두면 필터 없이 바로 그릴 수 있다
tot = (panel.groupby(["분기시작일", "분기표기"], as_index=False)
            .agg(평균폐업률=("폐업률", "mean"), 평균개업률=("개업률", "mean")))
tot[["평균폐업률", "평균개업률"]] = tot[["평균폐업률", "평균개업률"]].round(3)
tot["산업대분류"] = "서울 전체"
print("\n  [참고] 분기별 서울 전체 추이")
print(tot[["분기표기", "평균폐업률", "평균개업률"]].to_string(index=False))

# ------------------------------------------------------------------
# 2. 업종별 폐업률 순위
# ------------------------------------------------------------------
ind = (panel.groupby(["업종", "산업대분류"], as_index=False)
            .agg(점포수=("점포수", "sum"),
                 폐업점포수=("폐업점포수", "sum"),
                 평균폐업률=("폐업률", "mean"),
                 관측수=("폐업률", "size")))
ind = ind[ind["관측수"] >= 200].copy()
ind["실질폐업률"] = (ind["폐업점포수"] / ind["점포수"] * 100).round(3)
ind["평균폐업률"] = ind["평균폐업률"].round(3)
ind = ind.sort_values("평균폐업률", ascending=False)
ind.to_csv("tableau/tableau_industry.csv", index=False, encoding="utf-8-sig")
print(f"\n  tableau_industry.csv   {len(ind):>5,}행  (업종별)")
print("\n  [참고] 폐업률 상위 5 / 하위 5")
print(ind.head(5)[["업종", "평균폐업률"]].to_string(index=False))
print(ind.tail(5)[["업종", "평균폐업률"]].to_string(index=False))
