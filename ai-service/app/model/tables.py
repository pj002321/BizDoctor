"""DB 테이블 정의 — ERD(docs/schema.png, revised) 기준.

이 파일은 '서버가 기대하는 스키마'다. 실제 DDL 은 supabase/migrations/20261004090100_market_tables.sql
이 정한다. 둘이 어긋나면 쿼리가 터지므로 한쪽을 바꾸면 다른 쪽도 바꾼다.

원천 테이블(dim_* · fact_panel)은 pipeline/load/load_market.py 가 채우고, 나머지
(v_featured · fact_region_risk · region_summary · quarterly_trend · industry_rank)는
원천에서 계산하는 머티리얼라이즈드 뷰다. 여기서는 조회만 하므로 Table 로 선언해 둔다.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

dim_district = Table(
    "dim_district", metadata,
    Column("district_code", String, primary_key=True),
    Column("district_name", String, nullable=False),
    Column("gu_code", String, nullable=False),
    Column("gu_name", String, nullable=False),
)

dim_industry = Table(
    "dim_industry", metadata,
    Column("industry_code", String, primary_key=True),
    Column("industry_name", String, nullable=False),
    Column("kosis_industry1", String, nullable=True),
)

dim_kosis_industry1 = Table(
    "dim_kosis_industry1", metadata,
    Column("kosis_industry1", String, primary_key=True),
    Column("cost_increase_prob", Float),
)

fact_panel = Table(
    "fact_panel", metadata,
    Column("district_code", String, primary_key=True),
    Column("industry_code", String, primary_key=True),
    Column("quarter_code", String, primary_key=True),
    Column("store_count", Integer),
    Column("open_rate", Float),
    Column("closure_rate", Float),
    Column("closed_store_count", Integer),
    Column("franchise_store_count", Integer),
)

v_featured = Table(
    "v_featured", metadata,
    Column("district_code", String, primary_key=True),
    Column("industry_code", String, primary_key=True),
    Column("quarter_code", String, primary_key=True),
    Column("next_quarter_closure_rate", Float),
    Column("closure_rate_change", Float),
    Column("closure_rate_2q_avg", Float),
    Column("open_close_gap", Float),
    Column("franchise_ratio", Float),
    Column("closure_pctl_in_industry", Float),
)

fact_region_risk = Table(
    "fact_region_risk", metadata,
    Column("district_code", String, primary_key=True),
    Column("kosis_industry1", String, primary_key=True),
    Column("quarter_count", Integer),
    Column("avg_closure_rate", Float),
    Column("risk_weight", Float),
    Column("open_close_gap", Float),
    Column("store_count_sum", Integer),
    Column("risk_rank", Float),
)

region_summary = Table(
    "region_summary", metadata,
    Column("gu_name", String, primary_key=True),
    Column("kosis_industry1", String, primary_key=True),
    Column("store_count", Integer),
    Column("closed_store_count", Integer),
    Column("avg_closure_rate", Float),
    Column("avg_open_rate", Float),
    Column("risk_weight", Float),
    Column("observation_count", Integer),
    Column("real_closure_rate", Float),
    Column("risk_rank", Float),
)

quarterly_trend = Table(
    "quarterly_trend", metadata,
    Column("quarter_code", String, primary_key=True),
    Column("kosis_industry1", String, primary_key=True),
    Column("store_count", Integer),
    Column("closed_store_count", Integer),
    Column("avg_closure_rate", Float),
    Column("avg_open_rate", Float),
    Column("real_closure_rate", Float),
)

industry_rank = Table(
    "industry_rank", metadata,
    Column("industry_code", String, primary_key=True),
    Column("industry_name", String, nullable=False),
    Column("kosis_industry1", String),
    Column("store_count", Integer),
    Column("closed_store_count", Integer),
    Column("avg_closure_rate", Float),
    Column("observation_count", Integer),
    Column("real_closure_rate", Float),
)

diagnosis = Table(
    "diagnosis", metadata,
    Column("diagnosis_id", UUID(as_uuid=True), primary_key=True),
    Column("district_code", String, nullable=False),
    Column("industry_code", String, nullable=False),
    Column("sales_index", JSONB, nullable=False),
    Column("signal", JSONB, nullable=False),
    Column("feature_fallback", Boolean, nullable=False, default=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=True),
)
