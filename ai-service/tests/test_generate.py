import pytest

from app.ai import generate as g
from app.ai.generate import RecommendationRequest, Report

DOC = {"doc_id": "semas-a", "title": "2026년 소상공인 대환대출", "agency": "소진공", "limit_text": "최대 5,000만원",
       "rate_text": "연 4.5% 고정금리", "apply_end": None, "section": "지원한도", "evidence": "[대환대출 · 지원한도] 최대 5천만원"}
GOOD = Report(summary="고금리 부담이 추정됩니다.", recommendations=[RecommendationRequest(doc_id="semas-a", reason="최대 5,000만원, 연 4.5%")])
BAD = Report(summary="최대 1억원까지 됩니다.", recommendations=[RecommendationRequest(doc_id="made-up", reason="")])


def _fake(*answers):
    it = iter(answers)
    return lambda *a: next(it)


@pytest.fixture(autouse=True)
def _claude_agrees(monkeypatch):
    monkeypatch.setattr(g, "cross_check", lambda *a: [])


def test_passes_first_try(monkeypatch):
    monkeypatch.setattr(g, "_ask", _fake(GOOD))
    assert g.generate_report("고금리_과다채무형", 0.6, [DOC]) == (GOOD, [])


def test_retries_once_then_passes(monkeypatch):
    monkeypatch.setattr(g, "_ask", _fake(BAD, GOOD))
    assert g.generate_report("고금리_과다채무형", 0.6, [DOC]) == (GOOD, [])


def test_falls_back_to_template(monkeypatch):
    monkeypatch.setattr(g, "_ask", _fake(BAD, BAD))
    report, problems = g.generate_report("고금리_과다채무형", 0.6, [DOC])
    assert [r.doc_id for r in report.recommendations] == ["semas-a"]
    assert problems == ["근거에 없는 숫자: 100000000원", "검색 결과에 없는 문서: made-up"]
    assert g.verify(report, [DOC]) == []  # 템플릿은 가드레일을 항상 통과해야 한다

def test_claude_rejects_twice_then_template(monkeypatch):
    monkeypatch.setattr(g, "_ask", _fake(GOOD, GOOD))
    monkeypatch.setattr(g, "cross_check", lambda *a: ["근거 없는 주장: 폐업자도 신청 가능"])
    report, problems = g.generate_report("고금리_과다채무형", 0.6, [DOC])
    assert report != GOOD and problems == ["근거 없는 주장: 폐업자도 신청 가능"]
