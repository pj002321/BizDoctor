"""도구 응답 모양: DB 없이 retrieve를 바꿔 끼워 본다."""
from app.tools import policy

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