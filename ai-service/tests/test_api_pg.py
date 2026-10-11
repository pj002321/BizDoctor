# [역할] 통합 테스트 — 실제 Postgres 에 데이터를 넣고 모든 엔드포인트를 라우트부터 SQL 까지 검증한다.
"""실제 Postgres 에 붙여 라우트 → 서비스 → SQL 까지 돌린다.

TEST_DATABASE_URL 이 없으면 건너뛴다. 예:
  TEST_DATABASE_URL=postgresql+psycopg2://postgres@localhost:5432/biz_test pytest tests/test_api_pg.py
테이블을 지우고 다시 만드므로 운영 DB 를 가리키지 않는다.
"""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 환경변수 읽기.
import os
# 시각 계산(만료 테스트용).
from datetime import UTC, datetime, timedelta
# 없는 진단 ID 를 만들기 위한 UUID 생성.
from uuid import uuid4

# 테스트 프레임워크.
import pytest
# 서버를 띄우지 않고 앱에 HTTP 요청을 보내는 클라이언트.
from fastapi.testclient import TestClient
# 테스트용 엔진 생성, INSERT·UPDATE 문.
from sqlalchemy import create_engine, insert, update
# 테스트용 세션 공장.
from sqlalchemy.orm import sessionmaker

# 설정(토큰·기준 분기를 테스트 중에 바꾼다).
from app.core import config
# 원래 DB 의존성 — 테스트 DB 로 바꿔치기할 대상.
from app.core.db import get_db
# 위험 유형 타입.
from app.domain.risk_type import RiskType
# 테스트할 FastAPI 앱.
from app.main import app
# 테이블 정의 전체.
from app.model import tables as T
# 정책자금 한 건 스키마.
from app.schemas.signal import Solution
# 가짜 모델이 돌려줄 예측 타입.
from app.service.diagnosis_service import Prediction

# 테스트 DB 주소(환경변수).
URL = os.getenv("TEST_DATABASE_URL")
# 주소가 없으면 이 파일의 모든 테스트를 건너뛴다.
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL 미설정")

# 테스트에 쓸 산업대분류 두 개.
FOOD, EDU = "숙박 및 음식점업", "교육 서비스업"
# 이름이 같은 두 신사동(강남·관악)과 서교동의 행정동 코드.
GANGNAM_SINSA, GWANAK_SINSA, SEOGYO = "11680510", "11620685", "11440660"


# fact_panel 한 행과 v_featured 한 행을 함께 만들어 주는 도우미.
def _panel(d, i, q, n, close, open_, pctl, fr=0.1):
    # (원자료 행, 피처 행) 튜플을 돌려준다.
    return (
        # fact_panel 행: 행정동·업종·분기·점포 수·개업률·폐업률 등.
        dict(district_code=d, industry_code=i, quarter_code=q, store_count=n, open_rate=open_,
             # 폐업률과 나머지 카운트
             closure_rate=close, closed_store_count=0, franchise_store_count=0),
        # v_featured 행: 같은 키 + 폐업개업격차·프랜차이즈 비중·percentile.
        dict(district_code=d, industry_code=i, quarter_code=q, open_close_gap=close - open_,
             # 프랜차이즈 비중과 percentile
             franchise_ratio=fr, closure_pctl_in_industry=pctl),
    )


# 이 파일 전용 스키마 — 적재·마이그레이션 테스트(test_load_pg.py)와 같은 DB 를 써도 부딪히지 않게.
SCHEMA = "api_test"


# 테스트 모듈 전체에서 한 번만 실행: 테이블을 만들고 테스트 데이터를 넣는다.
@pytest.fixture(scope="module")
def engine():
    # 스키마를 새로 만들기 위한 관리용 엔진.
    admin = create_engine(URL)
    # 트랜잭션을 열고
    with admin.begin() as c:
        # 이전 실행의 스키마를 통째로 지우고
        c.exec_driver_sql(f"drop schema if exists {SCHEMA} cascade")
        # 새로 만든다.
        c.exec_driver_sql(f"create schema {SCHEMA}")
    # 관리용 엔진을 정리한다.
    admin.dispose()
    # 모든 연결의 기본 스키마를 api_test 로 둔 테스트 엔진.
    eng = create_engine(URL, connect_args={"options": f"-csearch_path={SCHEMA}"})
    # 정의된 테이블을 모두 만든다.
    T.metadata.create_all(eng)  # 이 테스트에선 머티리얼라이즈드 뷰들도 일반 테이블로 만들어 값을 직접 넣는다
    # 패널 테스트 데이터(원자료+피처 쌍).
    panel = [
        # 강남 신사동 한식, 2025Q3
        _panel(GANGNAM_SINSA, "CS100001", "20253", 30, 4.0, 3.0, 0.70),
        # 강남 신사동 한식, 2025Q4(최신 분기)
        _panel(GANGNAM_SINSA, "CS100001", "20254", 28, 6.0, 2.0, 0.90),
        # 관악 신사동 한식, 2025Q4
        _panel(GWANAK_SINSA, "CS100001", "20254", 12, 2.0, 2.5, 0.40),
        # 서교동 한식: 점포 3개, 프랜차이즈 비중 없음
        _panel(SEOGYO, "CS100001", "20254", 3, 33.3, 0.0, 0.95, fr=None),  # 표본 적음
        # 서교동 신규업종(KOSIS 매핑 없음)
        _panel(SEOGYO, "CS999999", "20254", 10, 1.0, 1.0, 0.50),           # KOSIS 미매핑 업종
    ]
    # 트랜잭션을 열고 끝나면 자동 확정한다.
    with eng.begin() as c:
        # 행정동 기준표를 넣는다.
        c.execute(insert(T.dim_district), [
            # 강남구 신사동
            dict(district_code=GANGNAM_SINSA, district_name="신사동", gu_code="11680", gu_name="강남구"),
            # 관악구 신사동(이름 같음)
            dict(district_code=GWANAK_SINSA, district_name="신사동", gu_code="11620", gu_name="관악구"),
            # 마포구 서교동
            dict(district_code=SEOGYO, district_name="서교동", gu_code="11440", gu_name="마포구"),
            # 강남구 대치2동(위험 데이터 없음 → 표본부족 확인용)
            dict(district_code="11680600", district_name="대치2동", gu_code="11680", gu_name="강남구"),
        ])
        # 업종 기준표를 넣는다.
        c.execute(insert(T.dim_industry), [
            # 한식 — 음식점업
            dict(industry_code="CS100001", industry_name="한식음식점", kosis_industry1=FOOD),
            # 학원 — 교육 서비스업(패널 데이터 없음)
            dict(industry_code="CS200001", industry_name="일반교습학원", kosis_industry1=EDU),
            # 매핑 안 된 업종
            dict(industry_code="CS999999", industry_name="신규업종", kosis_industry1=None),
        ])
        # 원자료 행들을 넣는다.
        c.execute(insert(T.fact_panel), [p for p, _ in panel])
        # 피처 행들을 넣는다.
        c.execute(insert(T.v_featured), [v for _, v in panel])
        # 행정동×산업 위험 가중치를 넣는다.
        c.execute(insert(T.fact_region_risk), [
            # 강남 신사동 음식점업: 순위 0.90(RED)
            dict(district_code=GANGNAM_SINSA, kosis_industry1=FOOD, quarter_count=11, avg_closure_rate=4.1,
                 # 위험가중치·격차·점포 합·순위
                 risk_weight=0.90, open_close_gap=1.2, store_count_sum=300, risk_rank=0.90),
            # 관악 신사동 음식점업: 순위 0.20(GREEN)
            dict(district_code=GWANAK_SINSA, kosis_industry1=FOOD, quarter_count=11, avg_closure_rate=2.0,
                 # 위험가중치·격차·점포 합·순위
                 risk_weight=0.40, open_close_gap=-0.5, store_count_sum=150, risk_rank=0.20),
        ])
        # 자치구 요약을 넣는다.
        c.execute(insert(T.region_summary), [
            # 강남구 음식점업(점포 300)
            dict(gu_name="강남구", kosis_industry1=FOOD, store_count=300, closed_store_count=12,
                 # 나머지 지표
                 avg_closure_rate=4.0, avg_open_rate=3.0, risk_weight=0.53, observation_count=50, real_closure_rate=4.0,
                 # 위험 순위(RED)
                 risk_rank=0.95),
            # 강남구 교육(점포 3 → 기본 필터에서 빠져야 함)
            dict(gu_name="강남구", kosis_industry1=EDU, store_count=3, closed_store_count=1,
                 # 나머지 지표
                 avg_closure_rate=33.3, avg_open_rate=0, risk_weight=0.51, observation_count=8, real_closure_rate=33.3,
                 # 위험 순위
                 risk_rank=0.70),
            # 관악구 음식점업(순위 0.70 → YELLOW)
            dict(gu_name="관악구", kosis_industry1=FOOD, store_count=100, closed_store_count=2,
                 # 나머지 지표
                 avg_closure_rate=2.0, avg_open_rate=2.5, risk_weight=0.51, observation_count=40, real_closure_rate=2.0,
                 # 위험 순위(YELLOW)
                 risk_rank=0.70),
        ])
        # 분기 추이를 넣는다.
        c.execute(insert(T.quarterly_trend), [
            # 각 분기 행을 만든다.
            dict(quarter_code=q, kosis_industry1=FOOD, store_count=1000, closed_store_count=10,
                 # 폐업률·개업률
                 avg_closure_rate=cl, avg_open_rate=op, real_closure_rate=cl)
            # 2023Q4 는 개업>폐업, 2024Q1 부터 폐업>개업(역전)
            for q, op, cl in [("20234", 3.0, 2.5), ("20241", 2.4, 2.6), ("20242", 2.3, 2.7)]
        ])
        # 업종 랭킹을 넣는다.
        c.execute(insert(T.industry_rank), [
            # 평균폐업률 1위 PC방
            dict(industry_code="CS300001", industry_name="PC방", kosis_industry1="예술", store_count=500,
                 # 나머지 지표
                 closed_store_count=30, avg_closure_rate=5.99, observation_count=300, real_closure_rate=4.0),
            # 실질폐업률 기준이면 1위가 되는 동물병원
            dict(industry_code="CS400001", industry_name="동물병원", kosis_industry1="협회", store_count=500,
                 # 나머지 지표
                 closed_store_count=4, avg_closure_rate=0.75, observation_count=300, real_closure_rate=6.0),
        ])
    # 엔진을 테스트들에 넘겨준다.
    yield eng
    # 모든 테스트가 끝나면 연결을 정리한다.
    eng.dispose()


# 진짜 모델 대신 쓰는 가짜 진단 모델.
class FakePredictor:
    # 생성 시 받은 입력을 기록할 자리를 만든다.
    def __init__(self):
        # 마지막으로 받은 입력
        self.seen = None

    # 입력을 기록하고 항상 같은 예측을 돌려준다.
    def predict(self, prepared):
        # 테스트에서 확인할 수 있게 입력을 저장한다.
        self.seen = prepared
        # 고금리 채무형·확률 0.61·점수 32.
        return Prediction(risk_type=RiskType.고금리_과다채무형, risk_type_confidence=0.61, score=32)


# 진짜 RAG 대신 쓰는 가짜 정책 검색기.
class FakeFinder:
    # 항상 정책자금 한 건을 돌려준다.
    def find(self, risk_type, top_k=3):
        # 고정된 한 건
        return [Solution(title="새출발기금", agency="캠코", summary="채무조정", source_doc_id="DOC_1")]


# 테스트마다 실행: 앱이 테스트 DB 를 쓰도록 바꾼 클라이언트를 만든다.
@pytest.fixture()
def client(engine, monkeypatch):
    # 테스트 DB 에 묶인 세션 공장.
    Session = sessionmaker(bind=engine)

    # get_db 대신 쓸 의존성.
    def _db():
        # 세션을 연다.
        s = Session()
        # 끝나면 반드시 닫는다.
        try:
            # 라우트에 세션을 넘긴다.
            yield s
        # 성공·실패와 상관없이
        finally:
            # 세션을 닫는다.
            s.close()

    # 토큰 검사를 끈다.
    monkeypatch.setattr(config, "SERVICE_TOKEN", None)
    # 기준 분기를 'DB 최신 분기'로 둔다.
    monkeypatch.setattr(config, "FEATURE_BASE_QUARTER", None)
    # 앱의 DB 의존성을 테스트용으로 바꾼다.
    app.dependency_overrides[get_db] = _db
    # 모델·검색기를 비워 둔다(기본 상태).
    app.state.predictor, app.state.solution_finder = None, None
    # 테스트에 클라이언트를 넘긴다.
    yield TestClient(app)
    # 테스트 후 의존성 교체를 되돌린다.
    app.dependency_overrides.clear()
    # 모델·검색기도 다시 비운다.
    app.state.predictor, app.state.solution_finder = None, None


# --- F-MAP -------------------------------------------------------------------
# /regions: 최소 점포수 필터와 신호등 색.
def test_regions_min_store_and_light(client):
    # 강남구만 조회한다.
    r = client.get("/api/market/regions", params={"gu": "강남구"}).json()
    # 점포 3개인 교육은 빠지고 음식점업(RED)만 남아야 한다.
    assert [(i["kosis_industry1"], i["signal_light"]) for i in r["items"]] == [(FOOD, "RED")]  # 점포 3 → 제외
    # 적용된 필터는 gu 와 min_store_count.
    assert r["meta"]["applied_filters"] == ["gu", "min_store_count"]
    # 최소 점포수를 1 로 낮추고 기간 필터도 건다.
    r = client.get("/api/market/regions", params={"min_store_count": 1, "start_quarter": "2024Q1"}).json()
    # 3건이 다 나오고, 기간 필터는 무시됐다고 알려야 한다.
    assert len(r["items"]) == 3 and r["meta"]["ignored_filters"] == ["start_quarter"]
    # 관악구 음식점업(순위 0.70)은 YELLOW — 색은 위험가중치(0.51)가 아니라 순위로 정한다.
    assert {i["gu_name"]: i["signal_light"] for i in r["items"] if i["kosis_industry1"] == FOOD}["관악구"] == "YELLOW"


# /dongs: 이름이 같은 행정동이 섞이지 않는지.
def test_dongs_uses_code_not_name(client):
    # 신사동은 강남구·관악구에 다 있다. 코드로 조인하므로 섞이지 않아야 한다.
    r = client.get("/api/market/regions/강남구/dongs").json()
    # (행정동코드, 산업) → 항목 딕셔너리로 바꾼다.
    by = {(i["district_code"], i["kosis_industry1"]): i for i in r["items"]}
    # 강남 신사동 음식점업은 0.90·RED 여야 한다(관악 0.40 이 아니라).
    assert by[(GANGNAM_SINSA, FOOD)]["risk_weight"] == 0.90 and by[(GANGNAM_SINSA, FOOD)]["signal_light"] == "RED"
    # 데이터 없는 대치2동은 표본부족.
    assert by[("11680600", FOOD)]["sample_status"] == "insufficient"
    # 강남 신사동 교육도 표본부족.
    assert by[(GANGNAM_SINSA, EDU)]["sample_status"] == "insufficient"
    # 관악 신사동은 결과에 없어야 한다.
    assert all(i["district_code"] != GWANAK_SINSA for i in r["items"])


# /dongs: 없는 자치구는 404.
def test_dongs_unknown_gu(client):
    # 없는 구로 요청한다.
    assert client.get("/api/market/regions/없는구/dongs").status_code == 404


# /cells: 시계열·기간 필터·표본 적음.
def test_cells(client):
    # 강남 신사동 한식을 조회한다.
    r = client.get("/api/market/cells", params={"district_code": GANGNAM_SINSA, "industry_code": "CS100001"})
    # 200 이어야 한다(아니면 본문을 보여준다).
    assert r.status_code == 200, r.text
    # 분기 점들
    pts = r.json()["points"]
    # 두 분기가 순서대로, 점포 30개라 배지 없음.
    assert [p["quarter"] for p in pts] == ["2025Q3", "2025Q4"] and not pts[0]["small_sample"]
    # 시작 분기를 2025Q4 로 건다.
    r = client.get("/api/market/cells", params={"district_code": GANGNAM_SINSA, "industry_code": "CS100001",
                                                 # 기간 필터
                                                 "start_quarter": "2025Q4"}).json()
    # 2025Q4 만 남아야 한다.
    assert [p["quarter"] for p in r["points"]] == ["2025Q4"]
    # 점포 3개 셀: 기본 필터(5)로는 빠지고, min=1 이면 배지와 함께 나온다
    r = client.get("/api/market/cells", params={"district_code": SEOGYO, "industry_code": "CS100001"}).json()
    # 기본 필터에서는 비어 있다.
    assert r["points"] == []
    # 최소 점포수를 1 로 낮춰 다시 조회한다.
    r = client.get("/api/market/cells", params={"district_code": SEOGYO, "industry_code": "CS100001",
                                                 # 최소 점포수 1
                                                 "min_store_count": 1}).json()
    # 이제 나오고 '표본 적음' 이 켜져 있어야 한다.
    assert r["points"][0]["small_sample"] is True


# /cells: 업종 코드가 없으면 422.
def test_cells_requires_industry(client):
    # industry_code 없이 요청한다.
    assert client.get("/api/market/cells", params={"district_code": SEOGYO}).status_code == 422


# /trends: 추이와 역전 분기.
def test_trends_reversal(client):
    # 음식점업 추이를 조회한다.
    r = client.get("/api/market/trends", params={"industry_group": [FOOD]}).json()
    # 세 분기가 순서대로.
    assert [p["quarter"] for p in r["items"]] == ["2023Q4", "2024Q1", "2024Q2"]
    # 2024Q1 에 폐업률이 개업률을 앞질렀다는 역전 하나.
    assert r["reversals"] == [{"kosis_industry1": FOOD, "quarter": "2024Q1", "direction": "closure_over_open"}]


# /industries: 정렬·개수·범위 검증.
def test_industries(client):
    # 기본(평균폐업률) 정렬로 조회한다.
    r = client.get("/api/market/industries").json()
    # PC방이 1위, 순위는 1부터.
    assert [i["industry_name"] for i in r["items"]] == ["PC방", "동물병원"] and r["items"][0]["rank"] == 1
    # 실질폐업률 기준으로 1개만.
    r = client.get("/api/market/industries", params={"sort_by": "real_closure_rate", "top_n": 1}).json()
    # 동물병원 1건만.
    assert [i["industry_name"] for i in r["items"]] == ["동물병원"]
    # top_n 101 은 범위 밖이라 422.
    assert client.get("/api/market/industries", params={"top_n": 101}).status_code == 422


# 잘못된 필터 값은 422.
def test_bad_quarter_param(client):
    # 분기 형식이 DB 형식이면 422.
    assert client.get("/api/market/trends", params={"start_quarter": "20241"}).status_code == 422
    # 최소 점포수 0 은 422.
    assert client.get("/api/market/trends", params={"min_store_count": 0}).status_code == 422


# --- F-DIA -------------------------------------------------------------------
# 진단 요청 기본 본문.
BODY = {"district_code": GANGNAM_SINSA, "industry_code": "CS100001", "monthly_sales": [12_000_000, 11_000_000, 9_000_000]}


# 모델이 없으면 503.
def test_diagnosis_503_without_model(client):
    # 모델 없이 진단을 요청한다.
    r = client.post("/api/diagnosis", json=BODY)
    # 503 이어야 한다.
    assert r.status_code == 503


# 진단 입력 검증.
def test_diagnosis_input_validation(client):
    # 1개월차 0 → 422
    assert client.post("/api/diagnosis", json={**BODY, "monthly_sales": [0, 1, 1]}).status_code == 422
    # 2개월만 → 422
    assert client.post("/api/diagnosis", json={**BODY, "monthly_sales": [1, 1]}).status_code == 422
    # 없는 행정동 → 422
    assert client.post("/api/diagnosis", json={**BODY, "district_code": "99999999"}).status_code == 422
    # 정의 안 된 필드 → 422
    assert client.post("/api/diagnosis", json={**BODY, "extra": 1}).status_code == 422


# 진단 전체 흐름: 실행 → 저장 → 재조회 → 만료.
def test_diagnosis_full_flow(client, engine):
    # 가짜 모델을 만든다.
    p = FakePredictor()
    # 앱에 가짜 모델·검색기를 꽂는다.
    app.state.predictor, app.state.solution_finder = p, FakeFinder()
    # 진단을 요청한다.
    r = client.post("/api/diagnosis", json=BODY)
    # 200 이어야 한다.
    assert r.status_code == 200, r.text
    # 응답 본문
    body = r.json()
    # 고금리 채무형 → RED·red.
    assert body["risk_level"] == "RED" and body["visual_theme"] == "red"
    # 디버그 필드가 없어야 한다.
    assert "_similarity_score" not in str(body)

    # F-DIA-01/02: 모델 입력은 1개월차=1.0, 피처는 최신 분기(2025Q4)
    assert p.seen.sales_index == [100.0, 91.6667, 75.0]
    # 모델 시퀀스는 100 으로 나눈 값.
    assert p.seen.model_sequence == [[1.0], [0.916667], [0.75]]
    # 기준 분기와 percentile 이 최신 분기 값.
    assert p.seen.features.base_quarter == "2025Q4" and p.seen.features.closure_pctl_in_industry == 0.90
    # 폴백 없음.
    assert p.seen.features.fallbacks == []

    # F-DIA-08: 저장된 행에 실금액이 없다
    did = r.headers["X-Diagnosis-Id"]
    # DB 에 직접 붙어서
    with engine.connect() as c:
        # 저장된 진단 행을 읽는다.
        row = c.execute(T.diagnosis.select()).mappings().one()
    # 실금액 숫자가 없고 지수만 있어야 한다.
    assert "12000000" not in str(dict(row)) and row["sales_index"] == [100.0, 91.6667, 75.0]

    # 공유 링크로 재조회한다.
    pub = client.get(f"/api/diagnosis/{did}").json()
    # 유형은 보인다.
    assert pub["risk_type"] == "고금리_과다채무형"
    # 점수·지수는 보이지 않는다.
    assert "score" not in pub and "sales_index" not in pub

    # 만료 시각을 과거로 바꾼다.
    with engine.begin() as c:
        # 1초 전으로 설정
        c.execute(update(T.diagnosis).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    # 만료된 링크는 410.
    assert client.get(f"/api/diagnosis/{did}").status_code == 410
    # 없는 ID 는 404.
    assert client.get(f"/api/diagnosis/{uuid4()}").status_code == 404


# 정적 피처 폴백 규칙.
def test_feature_fallbacks(client):
    # 가짜 모델을 만든다.
    p = FakePredictor()
    # 앱에 꽂는다.
    app.state.predictor, app.state.solution_finder = p, FakeFinder()
    # KOSIS 미매핑 업종 → 전산업
    client.post("/api/diagnosis", json={**BODY, "district_code": SEOGYO, "industry_code": "CS999999"})
    # 산업대분류가 전산업으로 바뀌었는지.
    assert p.seen.features.kosis_industry1 == "전산업"
    # 폴백 기록이 남았는지.
    assert "kosis_industry1:전산업" in p.seen.features.fallbacks
    # 그 동네에 해당 업종 셀이 없음 → 업종 서울 중앙값
    client.post("/api/diagnosis", json={**BODY, "district_code": "11680600"})
    # 셀 없음 폴백 기록.
    assert "cell_missing:industry_median" in p.seen.features.fallbacks
    # percentile 이 업종 중앙값으로 채워졌는지.
    assert p.seen.features.closure_pctl_in_industry == pytest.approx(0.90)  # 0.40 / 0.90 / 0.95 의 중앙값
    # 셀은 있지만 franchise_ratio 가 NULL → 그 값만 중앙값
    client.post("/api/diagnosis", json={**BODY, "district_code": SEOGYO})
    # 그 피처 하나만 폴백됐는지.
    assert p.seen.features.fallbacks == ["franchise_ratio:industry_median"]
    # 업종 데이터 자체가 없음 → 422
    assert client.post("/api/diagnosis", json={**BODY, "industry_code": "CS200001"}).status_code == 422


# /context 가 /{id} 에 잡히지 않는지 + 위치 계산.
def test_context_route_not_captured_by_id(client):
    # 강남 신사동 한식의 위치를 조회한다.
    r = client.get("/api/diagnosis/context", params={"district_code": GANGNAM_SINSA, "industry_code": "CS100001"})
    # 200 이어야 한다.
    assert r.status_code == 200, r.text
    # 응답 본문
    b = r.json()
    # percentile 0.90 → 상위 10%, 기준 분기 2025Q4, 문구에 반영.
    assert b["top_percent"] == 10 and b["quarter"] == "2025Q4" and "상위 10%" in b["message"]
    # 분포에는 점포 5개 이상인 두 행정동만.
    assert sum(x["count"] for x in b["distribution"]) == 2  # 점포 3개 셀은 분포에서 제외
    # UUID 가 아닌 ID 는 422.
    assert client.get("/api/diagnosis/not-a-uuid").status_code == 422


# 서비스 토큰 검사.
def test_service_token(client, monkeypatch):
    # 토큰을 설정한다.
    monkeypatch.setattr(config, "SERVICE_TOKEN", "s3cret")
    # /health 는 토큰 없이 열려 있다 — 헤더를 못 붙이는 플랫폼 헬스체크용.
    assert client.get("/health").status_code == 200
    # /api/* 는 헤더가 없으면 401.
    assert client.get("/api/market/regions").status_code == 401
    # 틀린 토큰도 401.
    assert client.get("/api/market/regions", headers={"X-Service-Token": "wrong"}).status_code == 401
    # 올바른 헤더면 200.
    assert client.get("/api/market/regions", headers={"X-Service-Token": "s3cret"}).status_code == 200
