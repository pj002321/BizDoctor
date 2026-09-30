# -*- coding: utf-8 -*-
"""
상권 신호등 - 가상 매출 시계열 생성 (실통계 캘리브레이션)

설계 원칙:
  개별 가게의 월별 매출 시계열 원본은 공개 데이터로 존재하지 않음(국세청/카드사만 보유).
  따라서 두 개의 실제 통계로 시뮬레이션의 양 끝을 고정한다.
    1) 어느 동네·업종에서 시작할지 → 서울시 폐업률 패널데이터 (지역x업종 위험 기준선)
    2) 위험군이 어떤 사유로 부실화되는지 비율 → 신용보증기금 채권관리 데이터 (부실사유코드 분포)
  즉 "무작위 생성"이 아니라 "실제 분포로 캘리브레이션된 생성"임을 명확히 함.
"""
import numpy as np
import pandas as pd
import os
from pathlib import Path

# 입출력 경로는 전부 ai-service/data/ 기준이다. 어디서 실행해도 같은 파일을 읽고 쓴다.
os.chdir(Path(__file__).resolve().parents[2] / "data")

RNG = np.random.default_rng(42)
N_COMPANIES = 30000    # 생성할 가상 소상공인 수
# 3,000 → 30,000 상향 (2026-08-18)
#   최소 클래스(상권_침체_붕괴형)가 학습 9건에 불과해 class_weight 를 켜든 끄든
#   과잉경보/과소경보 중 하나로 무너졌다. BASE_RISK_RATE 상향과 함께 적용해
#   최소 클래스를 약 293건까지 끌어올린다.
N_MONTHS = 6            # 최근 6개월 매출 시계열 (3개월 뒤 예측을 위해 앞 3개월 관찰 + 뒤 3개월 향방)

# ------------------------------------------------------------------
# 1. 실통계 로드
# ------------------------------------------------------------------
panel = pd.read_csv("seoul_panel_model_ready.csv")
# 가장 최근 분기만 사용 (2025년 4분기)
latest = panel[panel["기준_년분기_코드"] == panel["기준_년분기_코드"].max()].copy()

# 신보 부실사유코드 분포 (176번 파일)
sgf = None
for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
    try:
        sgf = pd.read_csv("raw/sgf176_utf8_bom.csv", encoding=enc)
        print(f"인코딩 {enc}로 성공")
        break
    except UnicodeDecodeError:
        continue
if sgf is None:
    sgf = pd.read_csv("raw/sgf176_utf8.csv", encoding="utf-8", encoding_errors="replace")
    print("모든 인코딩 실패, 깨진 문자 무시하고 강제로 읽음")

# KOSIS 애로사항 데이터 기반 YELLOW 세부유형(업종별) 실통계 확률
# 원가상승_확률 = (원재료비+최저임금영향) / (원재료비+최저임금영향+동일업종경쟁심화+보증금월세)
# 값이 높을수록 그 업종은 "원가_상승_부담형", 낮을수록 "단기_매출_정체형" 쪽으로 배정
yellow_prob = pd.read_csv("yellow_subtype_prob.csv").set_index("KOSIS_산업1")["원가상승_확률"]

# 컬럼명이 인코딩 손상으로 깨져있을 수 있어서, 이름 대신 위치(7번째 컬럼)로 찾음
# 원본 순서: 1채권관리ID 2최종업종차수 3제품명 4매출실적금액 5기업규모코드 6부실처리일자 7부실사유코드
sgf = sgf.rename(columns={sgf.columns[6]: "부실사유코드"})
print("7번째 컬럼 샘플값:", sgf["부실사유코드"].unique()[:5])

# ------------------------------------------------------------------
# 2. 부실사유코드 → risk_type 매핑 (기획서 4개 RED 유형 + 정상)
# ------------------------------------------------------------------
CAUSE_TO_RISKTYPE = {
    "휴.폐업": "상권_침체_붕괴형",
    "사업장 권리침해": "상권_침체_붕괴형",
    "원금연체": "고금리_과다채무형",
    "이자연체": "고금리_과다채무형",
    "이행지체": "고금리_과다채무형",
    "당좌부도": "고금리_과다채무형",
    "신용관리정보등록": "매출_폭락형",
    "대표자 등 부실사유발생(신용악화인정)": "매출_폭락형",
    "관계회사 사고에 의한 부실": "매출_폭락형",
    "연대보증에 따른 부실(연쇄도산)": "매출_폭락형",
    "회생절차,파산 신청": "고금리_과다채무형",   # 최고위험 → RED 중 가장 심각한 유형에 포함
    "제3자인수,합병에 의한 부실": "매출_폭락형",
    "신용회복지원신청": "고금리_과다채무형",
    "기타": "매출_폭락형",
}
sgf["risk_type"] = sgf["부실사유코드"].map(CAUSE_TO_RISKTYPE)
sgf["risk_type"] = sgf["risk_type"].fillna("매출_폭락형")  # 매핑 안 된 값은 기본값으로
cause_dist = sgf["risk_type"].value_counts(normalize=True)
print("=== 신보 데이터 기반 RED risk_type 분포 (부실기업 중) ===")
print(cause_dist)
print()

# ------------------------------------------------------------------
# 3. 가상 회사 N개 생성: (행정동, 업종) 쌍을 실제 점포수 비중으로 샘플링
# ------------------------------------------------------------------
weights = latest["점포_수"].clip(lower=1)
sampled_idx = RNG.choice(latest.index, size=N_COMPANIES, p=weights / weights.sum())
companies = latest.loc[sampled_idx, ["행정동_코드", "행정동_코드_명", "서비스_업종_코드_명", "KOSIS_산업1", "폐업률_업종내_percentile", "폐업_률", "개업_율", "프랜차이즈_비중"]].reset_index(drop=True)
companies["company_id"] = ["SGB_" + str(i).zfill(6) for i in range(N_COMPANIES)]

# ------------------------------------------------------------------
# 4. 위험군 여부 결정: 업종 내 폐업률 percentile을 사전확률로 사용
#    (percentile이 높을수록 = 실제로 그 업종/동네에서 폐업이 잦을수록 위험군 확률 ↑)
# ------------------------------------------------------------------
BASE_RISK_RATE = 0.30   # 전체 중 위험군(YELLOW+RED) 비중 목표치
# 0.12 → 0.30 상향 (2026-08-18)
#   학습을 위한 "의도적 과표집"이다. 실제 서울 위험군 비중은 약 14%이므로,
#   서비스 적용 시에는 예측 확률을 실제 사전확률로 보정(prior correction)해
#   되돌려야 한다. 보정하지 않으면 모든 사업자의 위험도가 과대 추정된다.
risk_prob = companies["폐업률_업종내_percentile"].fillna(0.5) * BASE_RISK_RATE * 2
risk_prob = risk_prob.clip(0, 0.9)
companies["is_at_risk"] = RNG.uniform(size=N_COMPANIES) < risk_prob

# 위험군 중에서도 RED(심각) vs YELLOW(주의) 구분 — percentile 상위 25% 안이면 RED
red_cut = companies["폐업률_업종내_percentile"].quantile(0.75)
companies["risk_level"] = "GREEN"
companies.loc[companies["is_at_risk"] & (companies["폐업률_업종내_percentile"] < red_cut), "risk_level"] = "YELLOW"
companies.loc[companies["is_at_risk"] & (companies["폐업률_업종내_percentile"] >= red_cut), "risk_level"] = "RED"

# ------------------------------------------------------------------
# 5. risk_type 배정
#    - RED: 신보 부실사유코드 실제 분포(cause_dist)대로 샘플링
#    - YELLOW: KOSIS 애로사항 데이터의 업종별 원가상승_확률로 샘플링 (실통계 기반, 50:50 아님)
#    - GREEN: 정상_유지형
# ------------------------------------------------------------------
DEFAULT_YELLOW_PROB = yellow_prob.loc["전산업"]  # 매핑 안 되는 업종 대비 기본값

def assign_risk_type(row):
    if row["risk_level"] == "RED":
        return RNG.choice(cause_dist.index, p=cause_dist.values)
    elif row["risk_level"] == "YELLOW":
        p_cost = yellow_prob.get(row["KOSIS_산업1"], DEFAULT_YELLOW_PROB)
        return RNG.choice(
            ["원가_상승_부담형", "단기_매출_정체형"], p=[p_cost, 1 - p_cost]
        )
    else:
        return "정상_유지형"

companies["risk_type"] = companies.apply(assign_risk_type, axis=1)

# ------------------------------------------------------------------
# 6. 월별 매출 시계열 생성 (6개월)
#    - 시작 매출: 업종별 매출액규모 통계 대신, 임의 기준값(100)에서 출발 (상대적 추이가 핵심이므로)
#    - RED: 최근으로 갈수록 가파르게 하락 (월 -8~-15%) + 노이즈
#    - YELLOW: 완만하게 하락 또는 정체 (월 -2~-5%) + 노이즈
#    - GREEN: 안정적 유지~소폭 성장 (월 -1~+2%) + 노이즈
# ------------------------------------------------------------------
TREND_BY_LEVEL = {
    "RED": (-0.15, -0.08),
    "YELLOW": (-0.05, -0.02),
    "GREEN": (-0.01, 0.02),
}

sales_records = []
for _, row in companies.iterrows():
    lo, hi = TREND_BY_LEVEL[row["risk_level"]]
    monthly_rate = RNG.uniform(lo, hi)
    sales = 100.0
    for m in range(N_MONTHS):
        noise = RNG.normal(0, 0.04)
        sales *= (1 + monthly_rate + noise)
        sales_records.append({
            "company_id": row["company_id"],
            "월차": m + 1,
            "매출지수": round(max(sales, 0), 2),
        })

sales_ts = pd.DataFrame(sales_records)

# ------------------------------------------------------------------
# 7. score(0~100) 산출: 최근 3개월 대비 이전 3개월 매출 변화율 기반
# ------------------------------------------------------------------
pivot = sales_ts.pivot(index="company_id", columns="월차", values="매출지수")
recent3 = pivot[[4, 5, 6]].mean(axis=1)
prev3 = pivot[[1, 2, 3]].mean(axis=1)
decline_rate = (prev3 - recent3) / prev3  # 양수면 매출 감소
score = (decline_rate.clip(-0.3, 1.0) * 100).clip(0, 100).round(1)
companies = companies.merge(score.rename("score"), left_on="company_id", right_index=True)

# ------------------------------------------------------------------
# 8. 저장
# ------------------------------------------------------------------
companies.to_csv("synthetic_companies.csv", index=False, encoding="utf-8-sig")
sales_ts.to_csv("synthetic_sales_timeseries.csv", index=False, encoding="utf-8-sig")

print("=== 생성 결과 요약 ===")
print("총 가상 회사 수:", len(companies))
print()
print("risk_level 분포:")
print(companies["risk_level"].value_counts())
print()
print("risk_type 분포:")
print(companies["risk_type"].value_counts())
print()
print("risk_level별 평균 score:")
print(companies.groupby("risk_level")["score"].mean())
print()
print("샘플 5건:")
print(companies[["company_id","행정동_코드_명","서비스_업종_코드_명","risk_level","risk_type","score"]].head())