"""실제 Postgres 에 붙여 라우트 → 서비스 → SQL 까지 돌린다.

TEST_DATABASE_URL 이 없으면 건너뛴다. 예:
  TEST_DATABASE_URL=postgresql+psycopg2://postgres@localhost:5432/biz_test pytest tests/test_api_pg.py
테이블을 지우고 다시 만드므로 운영 DB 를 가리키지 않는다.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert, update
from sqlalchemy.orm import sessionmaker

from app.core import config
from app.core.db import get_db
from app.domain.risk_type import RiskType
from app.main import app
from app.model import tables as T
from app.schemas.signal import Solution
from app.service.diagnosis_service import Prediction

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL 미설정")

FOOD, EDU = "숙박 및 음식점업", "교육 서비스업"
GANGNAM_SINSA, GWANAK_SINSA, SEOGYO = "11680510", "11620685", "11440660"


def _panel(d, i, q, n, close, open_, pctl, fr=0.1):
    return (
        dict(district_code=d, industry_code=i, quarter_code=q, store_count=n, open_rate=open_,
             closure_rate=close, closed_store_count=0, franchise_store_count=0),
        dict(district_code=d, industry_code=i, quarter_code=q, open_close_gap=close - open_,
             franchise_ratio=fr, closure_pctl_in_industry=pctl),
    )


SCHEMA = "api_test"


@pytest.fixture(scope="module")
def engine():
    admin = create_engine(URL)
    with admin.begin() as c:
        c.exec_driver_sql(f"drop schema if exists {SCHEMA} cascade")
        c.exec_driver_sql(f"create schema {SCHEMA}")
    admin.dispose()
    eng = create_engine(URL, connect_args={"options": f"-csearch_path={SCHEMA}"})
    T.metadata.create_all(eng)
    panel = [
        _panel(GANGNAM_SINSA, "CS100001", "20253", 30, 4.0, 3.0, 0.70),
        _panel(GANGNAM_SINSA, "CS100001", "20254", 28, 6.0, 2.0, 0.90),
        _panel(GWANAK_SINSA, "CS100001", "20254", 12, 2.0, 2.5, 0.40),
        _panel(SEOGYO, "CS100001", "20254", 3, 33.3, 0.0, 0.95, fr=None),
        _panel(SEOGYO, "CS999999", "20254", 10, 1.0, 1.0, 0.50),
    ]
    with eng.begin() as c:
        c.execute(insert(T.dim_district), [
            dict(district_code=GANGNAM_SINSA, district_name="신사동", gu_code="11680", gu_name="강남구"),
            dict(district_code=GWANAK_SINSA, district_name="신사동", gu_code="11620", gu_name="관악구"),
            dict(district_code=SEOGYO, district_name="서교동", gu_code="11440", gu_name="마포구"),
            dict(district_code="11680600", district_name="대치2동", gu_code="11680", gu_name="강남구"),
        ])
        c.execute(insert(T.dim_industry), [
            dict(industry_code="CS100001", industry_name="한식음식점", kosis_industry1=FOOD),
            dict(industry_code="CS200001", industry_name="일반교습학원", kosis_industry1=EDU),
            dict(industry_code="CS999999", industry_name="신규업종", kosis_industry1=None),
        ])
        c.execute(insert(T.fact_panel), [p for p, _ in panel])
        c.execute(insert(T.v_featured), [v for _, v in panel])
        c.execute(insert(T.fact_region_risk), [
            dict(district_code=GANGNAM_SINSA, kosis_industry1=FOOD, quarter_count=11, avg_closure_rate=4.1,
                 risk_weight=0.90, open_close_gap=1.2, store_count_sum=300, risk_rank=0.90),
            dict(district_code=GWANAK_SINSA, kosis_industry1=FOOD, quarter_count=11, avg_closure_rate=2.0,
                 risk_weight=0.40, open_close_gap=-0.5, store_count_sum=150, risk_rank=0.20),
        ])
        c.execute(insert(T.region_summary), [
            dict(gu_name="강남구", kosis_industry1=FOOD, store_count=300, closed_store_count=12,
                 avg_closure_rate=4.0, avg_open_rate=3.0, risk_weight=0.53, observation_count=50, real_closure_rate=4.0,
                 risk_rank=0.95),
            dict(gu_name="강남구", kosis_industry1=EDU, store_count=3, closed_store_count=1,
                 avg_closure_rate=33.3, avg_open_rate=0, risk_weight=0.51, observation_count=8, real_closure_rate=33.3,
                 risk_rank=0.70),
            dict(gu_name="관악구", kosis_industry1=FOOD, store_count=100, closed_store_count=2,
                 avg_closure_rate=2.0, avg_open_rate=2.5, risk_weight=0.51, observation_count=40, real_closure_rate=2.0,
                 risk_rank=0.70),
        ])
        c.execute(insert(T.quarterly_trend), [
            dict(quarter_code=q, kosis_industry1=FOOD, store_count=1000, closed_store_count=10,
                 avg_closure_rate=cl, avg_open_rate=op, real_closure_rate=cl)
            for q, op, cl in [("20234", 3.0, 2.5), ("20241", 2.4, 2.6), ("20242", 2.3, 2.7)]
        ])
        c.execute(insert(T.industry_rank), [
            dict(industry_code="CS300001", industry_name="PC방", kosis_industry1="예술", store_count=500,
                 closed_store_count=30, avg_closure_rate=5.99, observation_count=300, real_closure_rate=4.0),
            dict(industry_code="CS400001", industry_name="동물병원", kosis_industry1="협회", store_count=500,
                 closed_store_count=4, avg_closure_rate=0.75, observation_count=300, real_closure_rate=6.0),
        ])
    yield eng
    eng.dispose()


class FakePredictor:
    def __init__(self):
        self.seen = None

    def predict(self, prepared):
        self.seen = prepared
        return Prediction(risk_type=RiskType.고금리_과다채무형, risk_type_confidence=0.61, score=32)


class FakeFinder:
    def find(self, risk_type, top_k=3):
        return [Solution(title="새출발기금", agency="캠코", summary="채무조정", source_doc_id="DOC_1")]


@pytest.fixture()
def client(engine, monkeypatch):
    Session = sessionmaker(bind=engine)

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    monkeypatch.setattr(config, "SERVICE_TOKEN", None)
    monkeypatch.setattr(config, "FEATURE_BASE_QUARTER", None)
    app.dependency_overrides[get_db] = _db
    app.state.predictor, app.state.solution_finder = None, None
    yield TestClient(app)
    app.dependency_overrides.clear()
    app.state.predictor, app.state.solution_finder = None, None


def test_regions_min_store_and_light(client):
    r = client.get("/api/market/regions", params={"gu": "강남구"}).json()
    assert [(i["kosis_industry1"], i["signal_light"]) for i in r["items"]] == [(FOOD, "RED")]
    assert r["meta"]["applied_filters"] == ["gu", "min_store_count"]
    r = client.get("/api/market/regions", params={"min_store_count": 1, "start_quarter": "2024Q1"}).json()
    assert len(r["items"]) == 3 and r["meta"]["ignored_filters"] == ["start_quarter"]
    assert {i["gu_name"]: i["signal_light"] for i in r["items"] if i["kosis_industry1"] == FOOD}["관악구"] == "YELLOW"


def test_dongs_uses_code_not_name(client):
    r = client.get("/api/market/regions/강남구/dongs").json()
    by = {(i["district_code"], i["kosis_industry1"]): i for i in r["items"]}
    assert by[(GANGNAM_SINSA, FOOD)]["risk_weight"] == 0.90 and by[(GANGNAM_SINSA, FOOD)]["signal_light"] == "RED"
    assert by[("11680600", FOOD)]["sample_status"] == "insufficient"
    assert by[(GANGNAM_SINSA, EDU)]["sample_status"] == "insufficient"
    assert all(i["district_code"] != GWANAK_SINSA for i in r["items"])


def test_dongs_unknown_gu(client):
    assert client.get("/api/market/regions/없는구/dongs").status_code == 404


def test_cells(client):
    r = client.get("/api/market/cells", params={"district_code": GANGNAM_SINSA, "industry_code": "CS100001"})
    assert r.status_code == 200, r.text
    pts = r.json()["points"]
    assert [p["quarter"] for p in pts] == ["2025Q3", "2025Q4"] and not pts[0]["small_sample"]
    r = client.get("/api/market/cells", params={"district_code": GANGNAM_SINSA, "industry_code": "CS100001",
                                                 "start_quarter": "2025Q4"}).json()
    assert [p["quarter"] for p in r["points"]] == ["2025Q4"]
    r = client.get("/api/market/cells", params={"district_code": SEOGYO, "industry_code": "CS100001"}).json()
    assert r["points"] == []
    r = client.get("/api/market/cells", params={"district_code": SEOGYO, "industry_code": "CS100001",
                                                 "min_store_count": 1}).json()
    assert r["points"][0]["small_sample"] is True


def test_cells_requires_industry(client):
    assert client.get("/api/market/cells", params={"district_code": SEOGYO}).status_code == 422


def test_trends_reversal(client):
    r = client.get("/api/market/trends", params={"industry_group": [FOOD]}).json()
    assert [p["quarter"] for p in r["items"]] == ["2023Q4", "2024Q1", "2024Q2"]
    assert r["reversals"] == [{"kosis_industry1": FOOD, "quarter": "2024Q1", "direction": "closure_over_open"}]


def test_industries(client):
    r = client.get("/api/market/industries").json()
    assert [i["industry_name"] for i in r["items"]] == ["PC방", "동물병원"] and r["items"][0]["rank"] == 1
    r = client.get("/api/market/industries", params={"sort_by": "real_closure_rate", "top_n": 1}).json()
    assert [i["industry_name"] for i in r["items"]] == ["동물병원"]
    assert client.get("/api/market/industries", params={"top_n": 101}).status_code == 422


def test_bad_quarter_param(client):
    assert client.get("/api/market/trends", params={"start_quarter": "20241"}).status_code == 422
    assert client.get("/api/market/trends", params={"min_store_count": 0}).status_code == 422


BODY = {"district_code": GANGNAM_SINSA, "industry_code": "CS100001", "monthly_sales": [12_000_000, 11_000_000, 9_000_000]}


def test_diagnosis_503_without_model(client):
    r = client.post("/api/diagnosis", json=BODY)
    assert r.status_code == 503


def test_diagnosis_input_validation(client):
    assert client.post("/api/diagnosis", json={**BODY, "monthly_sales": [0, 1, 1]}).status_code == 422
    assert client.post("/api/diagnosis", json={**BODY, "monthly_sales": [1, 1]}).status_code == 422
    assert client.post("/api/diagnosis", json={**BODY, "district_code": "99999999"}).status_code == 422
    assert client.post("/api/diagnosis", json={**BODY, "extra": 1}).status_code == 422


def test_diagnosis_full_flow(client, engine):
    p = FakePredictor()
    app.state.predictor, app.state.solution_finder = p, FakeFinder()
    r = client.post("/api/diagnosis", json=BODY)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["risk_level"] == "RED" and body["visual_theme"] == "red"
    assert "_similarity_score" not in str(body)

    assert p.seen.sales_index == [100.0, 91.6667, 75.0]
    assert p.seen.model_sequence == [[1.0], [0.916667], [0.75]]
    assert p.seen.features.base_quarter == "2025Q4" and p.seen.features.closure_pctl_in_industry == 0.90
    assert p.seen.features.fallbacks == []

    did = r.headers["X-Diagnosis-Id"]
    with engine.connect() as c:
        row = c.execute(T.diagnosis.select()).mappings().one()
    assert "12000000" not in str(dict(row)) and row["sales_index"] == [100.0, 91.6667, 75.0]

    pub = client.get(f"/api/diagnosis/{did}").json()
    assert pub["risk_type"] == "고금리_과다채무형"
    assert "score" not in pub and "sales_index" not in pub

    with engine.begin() as c:
        c.execute(update(T.diagnosis).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    assert client.get(f"/api/diagnosis/{did}").status_code == 410
    assert client.get(f"/api/diagnosis/{uuid4()}").status_code == 404


def test_feature_fallbacks(client):
    p = FakePredictor()
    app.state.predictor, app.state.solution_finder = p, FakeFinder()
    client.post("/api/diagnosis", json={**BODY, "district_code": SEOGYO, "industry_code": "CS999999"})
    assert p.seen.features.kosis_industry1 == "전산업"
    assert "kosis_industry1:전산업" in p.seen.features.fallbacks
    client.post("/api/diagnosis", json={**BODY, "district_code": "11680600"})
    assert "cell_missing:industry_median" in p.seen.features.fallbacks
    assert p.seen.features.closure_pctl_in_industry == pytest.approx(0.90)
    client.post("/api/diagnosis", json={**BODY, "district_code": SEOGYO})
    assert p.seen.features.fallbacks == ["franchise_ratio:industry_median"]
    assert client.post("/api/diagnosis", json={**BODY, "industry_code": "CS200001"}).status_code == 422


def test_context_route_not_captured_by_id(client):
    r = client.get("/api/diagnosis/context", params={"district_code": GANGNAM_SINSA, "industry_code": "CS100001"})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["top_percent"] == 10 and b["quarter"] == "2025Q4" and "상위 10%" in b["message"]
    assert sum(x["count"] for x in b["distribution"]) == 2
    assert client.get("/api/diagnosis/not-a-uuid").status_code == 422


def test_service_token(client, monkeypatch):
    monkeypatch.setattr(config, "SERVICE_TOKEN", "s3cret")
    assert client.get("/health").status_code == 200
    assert client.get("/api/market/regions").status_code == 401
    assert client.get("/api/market/regions", headers={"X-Service-Token": "wrong"}).status_code == 401
    assert client.get("/api/market/regions", headers={"X-Service-Token": "s3cret"}).status_code == 200
