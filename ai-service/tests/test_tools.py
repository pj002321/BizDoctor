"""도구 응답 모양: DB 없이 retrieve를 바꿔 끼워 본다."""
from app.tools import policy, market
from types import SimpleNamespace


DOC = {"doc_id": "d1", "title": "2026년 소상공인 대환대출", "agency": "소진공", "limit_text": "5,000만원",
       "rate_text": "연 4.5%", "apply_start": None, "apply_end": None, "source_url": "https://x",
       "section": "지원내용", "evidence": "고정금리로 갈아탐", "must_read": None}


def test_공고를_찾으면_근거와_출처(monkeypatch):
    monkeypatch.setattr(policy, "retrieve", lambda q, rt, k: [(DOC, 0.03)])
    r = policy.search_policy("대환대출 금리")
    assert "「2026년 소상공인 대환대출」" in r["context"]
    assert r["sources"] == [{"docId": "d1", "title": "2026년 소상공인 대환대출"}]


def test_0건이면_둘_다_비어_있음(monkeypatch):
    monkeypatch.setattr(policy, "retrieve", lambda q, rt, k: [])
    assert policy.search_policy("코인 투자") == {"context": "", "sources": []}


def _cell(*points):
    return SimpleNamespace(district_name="망원1동", industry_name="커피-음료", points=list(points))


def _p(q, n, pctl=None):
    return SimpleNamespace(quarter=q, store_count=n, closure_rate=4.0, open_rate=1.9,
                           closure_pctl_in_industry=pctl, small_sample=n <= 5)


def test_상권_지표는_최근_4개_분기만(monkeypatch):
    pts = [_p(f"2024Q{i}", 40) for i in range(1, 5)] + [_p("2025Q1", 40, 0.78)]
    monkeypatch.setattr(market.market_service, "get_cells", lambda db, d, f: _cell(*pts))
    ctx = market.get_market_stats(None, "11440660", "CS100010")["context"]
    assert "2024Q1" not in ctx and "최근 4개 분기" in ctx
    assert ctx.endswith("상위 22%")


def test_점포_5개_이하는_표본_적음(monkeypatch):
    monkeypatch.setattr(market.market_service, "get_cells", lambda db, d, f: _cell(_p("2025Q1", 3)))
    assert "표본 적음" in market.get_market_stats(None, "11440660", "CS100010")["context"]