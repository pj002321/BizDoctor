# [역할] DB 테이블 정의 — ERD 기준으로 서버가 기대하는 테이블·컬럼(상권 패널·집계·진단 결과)을 선언한다.
"""DB 테이블 정의 — ERD(docs/schema.png, revised) 기준.

이 파일은 '서버가 기대하는 스키마'다. 실제 DDL 은 supabase/migrations/20261004090100_market_tables.sql
이 정한다. 둘이 어긋나면 쿼리가 터지므로 한쪽을 바꾸면 다른 쪽도 바꾼다.

원천 테이블(dim_* · fact_panel)은 pipeline/load/load_market.py 가 채우고, 나머지
(v_featured · fact_region_risk · region_summary · quarterly_trend · industry_rank)는
원천에서 계산하는 머티리얼라이즈드 뷰다. 여기서는 조회만 하므로 Table 로 선언해 둔다.
"""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 테이블·컬럼을 선언하는 SQLAlchemy Core 도구와 컬럼 타입들.
from sqlalchemy import (
    # 참/거짓
    Boolean,
    # 컬럼 선언
    Column,
    # 날짜+시각
    DateTime,
    # 실수
    Float,
    # 정수
    Integer,
    # 테이블 묶음(스키마) 객체
    MetaData,
    # 문자열
    String,
    # 테이블 선언
    Table,
)
# Postgres 전용 타입: JSONB(이진 JSON), UUID.
from sqlalchemy.dialects.postgresql import JSONB, UUID

# 아래 모든 테이블을 등록할 스키마 객체.
metadata = MetaData()

# --- 차원 -----------------------------------------------------------------
# 행정동 기준표(DIM_DISTRICT).
dim_district = Table(
    # 테이블 이름과 소속 스키마
    "dim_district", metadata,
    # 행정동 코드(PK).
    Column("district_code", String, primary_key=True),  # 행정동 코드. 이름은 중복된다(신사동 ×2) → 항상 코드로 조인
    # 행정동 이름
    Column("district_name", String, nullable=False),
    # 자치구 코드
    Column("gu_code", String, nullable=False),          # 행정동 코드 앞 5자리
    # 자치구 이름
    Column("gu_name", String, nullable=False),
)

# 서비스 업종 기준표(DIM_INDUSTRY).
dim_industry = Table(
    # 테이블 이름과 소속 스키마
    "dim_industry", metadata,
    # 업종 코드(PK).
    Column("industry_code", String, primary_key=True),  # 서비스_업종_코드 (CS…)
    # 업종 이름
    Column("industry_name", String, nullable=False),
    # KOSIS 산업대분류.
    Column("kosis_industry1", String, nullable=True),   # 미매핑이면 NULL → F-DIA-02 '전산업' 폴백
)

# KOSIS 산업대분류 기준표(DIM_KOSIS_INDUSTRY1).
dim_kosis_industry1 = Table(
    # 테이블 이름과 소속 스키마
    "dim_kosis_industry1", metadata,
    # 산업대분류 이름(PK)
    Column("kosis_industry1", String, primary_key=True),
    # YELLOW 안에서 원가상승형일 확률
    Column("cost_increase_prob", Float),
)

# --- 사실 ------------------------------------------------------------------
# 분기별 행정동×업종 원자료(FACT_PANEL).
fact_panel = Table(
    # 테이블 이름과 소속 스키마
    "fact_panel", metadata,
    # 행정동 코드(복합 PK 1)
    Column("district_code", String, primary_key=True),
    # 업종 코드(복합 PK 2)
    Column("industry_code", String, primary_key=True),
    # 분기 코드(복합 PK 3).
    Column("quarter_code", String, primary_key=True),   # '20254' (domain/quarter.py)
    # 점포 수
    Column("store_count", Integer),
    # 개업률
    Column("open_rate", Float),
    # 폐업률
    Column("closure_rate", Float),
    # 폐업 점포 수
    Column("closed_store_count", Integer),
    # 프랜차이즈 점포 수
    Column("franchise_store_count", Integer),
)

# 머티리얼라이즈드 뷰. 정적 피처(F-DIA-02)와 상세 카드(F-MAP-03)의 percentile 이 여기서 나온다.
# 2025Q4 행도 있다(그 행의 next_quarter_closure_rate 만 NULL).
v_featured = Table(
    # 뷰 이름과 소속 스키마
    "v_featured", metadata,
    # 행정동 코드
    Column("district_code", String, primary_key=True),
    # 업종 코드
    Column("industry_code", String, primary_key=True),
    # 분기 코드
    Column("quarter_code", String, primary_key=True),
    # 다음 분기 폐업률(학습 타깃)
    Column("next_quarter_closure_rate", Float),
    # 직전 분기 대비 폐업률 변화
    Column("closure_rate_change", Float),
    # 최근 2분기 폐업률 평균
    Column("closure_rate_2q_avg", Float),
    # 폐업률 - 개업률
    Column("open_close_gap", Float),
    # 프랜차이즈 비중
    Column("franchise_ratio", Float),
    # 같은 분기·업종 안에서의 폐업률 순위(0~1)
    Column("closure_pctl_in_industry", Float),
)

# 행정동×산업대분류 위험 가중치(FACT_REGION_RISK). 머티리얼라이즈드 뷰.
fact_region_risk = Table(
    # 테이블 이름과 소속 스키마
    "fact_region_risk", metadata,
    # 행정동 코드(복합 PK 1)
    Column("district_code", String, primary_key=True),
    # 산업대분류(복합 PK 2)
    Column("kosis_industry1", String, primary_key=True),
    # 관측된 분기 수
    Column("quarter_count", Integer),
    # 평균 폐업률
    Column("avg_closure_rate", Float),
    # 위험가중치(신호등 색 기준값)
    Column("risk_weight", Float),
    # ERD 에는 없지만 F-MAP-02 출력(폐업개업격차)과 최소 점포수 필터에 필요하다.
    # risk_weights.sql 의 '폐업개업격차', '연점포수' 와 같은 값이다.
    Column("open_close_gap", Float),
    # 연 점포 수 합계
    Column("store_count_sum", Integer),
    # 같은 산업대분류 행정동들 사이 위험가중치 순위(0~1) — 신호등 색 기준
    Column("risk_rank", Float),
)

# --- 사전 집계 (스펙.md 2장) -------------------------------------------------
# 자치구×산업 요약 — 지도용. 머티리얼라이즈드 뷰(200행).
region_summary = Table(
    # 테이블 이름과 소속 스키마
    "region_summary", metadata,
    # 자치구 이름(복합 PK 1)
    Column("gu_name", String, primary_key=True),
    # 산업대분류(복합 PK 2)
    Column("kosis_industry1", String, primary_key=True),
    # 점포 수 합계
    Column("store_count", Integer),
    # 폐업 점포 수 합계
    Column("closed_store_count", Integer),
    # 평균 폐업률
    Column("avg_closure_rate", Float),
    # 평균 개업률
    Column("avg_open_rate", Float),
    # 위험가중치 평균
    Column("risk_weight", Float),
    # 관측 수
    Column("observation_count", Integer),
    # 실질 폐업률(폐업 점포 합 / 점포 합)
    Column("real_closure_rate", Float),
    # 같은 산업대분류 자치구들 사이 위험가중치 순위(0~1) — 신호등 색 기준
    Column("risk_rank", Float),
)

# 분기×산업 추이 — 차트용. 머티리얼라이즈드 뷰(12분기 × 8산업 = 96행).
quarterly_trend = Table(
    # 테이블 이름과 소속 스키마
    "quarterly_trend", metadata,
    # 분기 코드(복합 PK 1)
    Column("quarter_code", String, primary_key=True),
    # 산업대분류(복합 PK 2)
    Column("kosis_industry1", String, primary_key=True),
    # 점포 수 합계
    Column("store_count", Integer),
    # 폐업 점포 수 합계
    Column("closed_store_count", Integer),
    # 평균 폐업률
    Column("avg_closure_rate", Float),
    # 평균 개업률
    Column("avg_open_rate", Float),
    # 실질 폐업률
    Column("real_closure_rate", Float),
)

# 업종별 폐업률 순위 — 막대 차트용. 머티리얼라이즈드 뷰(관측 200건 이상, 100행).
industry_rank = Table(
    # 테이블 이름과 소속 스키마
    "industry_rank", metadata,
    # 업종 코드(PK)
    Column("industry_code", String, primary_key=True),
    # 업종 이름
    Column("industry_name", String, nullable=False),
    # 산업대분류
    Column("kosis_industry1", String),
    # 점포 수 합계
    Column("store_count", Integer),
    # 폐업 점포 수 합계
    Column("closed_store_count", Integer),
    # 평균 폐업률
    Column("avg_closure_rate", Float),
    # 관측 수
    Column("observation_count", Integer),
    # 실질 폐업률
    Column("real_closure_rate", Float),
)

# --- 진단 결과 (F-DIA-08) ----------------------------------------------------
# 매출 실금액 컬럼은 없다(F-SYS-05). 지수만 저장한다.
diagnosis = Table(
    # 테이블 이름과 소속 스키마
    "diagnosis", metadata,
    # 진단 ID(PK, 파이썬에서는 uuid.UUID 로 다룬다)
    Column("diagnosis_id", UUID(as_uuid=True), primary_key=True),
    # 행정동 코드
    Column("district_code", String, nullable=False),
    # 업종 코드
    Column("industry_code", String, nullable=False),
    # 매출 지수 목록.
    Column("sales_index", JSONB, nullable=False),     # [100.0, 93.2, 88.1]
    # 프론트로 나간 신호 JSON.
    Column("signal", JSONB, nullable=False),          # F-RAG-04 신호 JSON
    # 정적 피처 폴백 사용 여부
    Column("feature_fallback", Boolean, nullable=False, default=False),
    # 생성 시각(시간대 포함)
    Column("created_at", DateTime(timezone=True), nullable=False),
    # 만료 시각.
    Column("expires_at", DateTime(timezone=True), nullable=True),  # 비로그인 24h. 로그인 사용자는 NULL
)
