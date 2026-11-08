"""챗봇 도구 루프: OpenAI 대신 정해진 응답을 차례로 내는 가짜를 끼운다."""
import json
from types import SimpleNamespace

from app.ai import chat as c


def _msg(content=None, calls=()):
    tool_calls = [SimpleNamespace(id=f"c{i}", function=SimpleNamespace(name=n, arguments=json.dumps(a)))
                  for i, (n, a) in enumerate(calls)]
    return SimpleNamespace(content=content, tool_calls=tool_calls or None)


def _fake(monkeypatch, *replies):
    sent = []
    it = iter(replies)

    def create(**kw):
        sent.append(kw)
        return SimpleNamespace(choices=[SimpleNamespace(message=next(it))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(c, "_get_client", lambda: client)
    return sent


POLICY = {"search_policy": lambda query: {"context": f"[근거 1] {query}", "sources": [{"docId": "d1", "title": "대환대출"}]}}


def test_도구를_부르고_결과로_답한다(monkeypatch):
    sent = _fake(monkeypatch, _msg(calls=[("search_policy", {"query": "대환대출 금리"})]), _msg("연 4.5%입니다."))
    answer, context, sources = c.chat("대환대출 금리?", [], POLICY)
    assert answer == "연 4.5%입니다."
    assert context == "[근거 1] 대환대출 금리"
    assert sources == [{"docId": "d1", "title": "대환대출"}]
    assert [t["function"]["name"] for t in sent[0]["tools"]] == ["search_policy"]  # 진단 없으면 상권 도구는 안 보임


def test_도구만_계속_부르면_거절(monkeypatch):
    loop = _msg(calls=[("search_policy", {"query": "x"})])
    _fake(monkeypatch, *[loop] * (c.MAX_TOOL_ROUNDS + 1))
    answer, _, _ = c.chat("?", [], POLICY)
    assert answer == c.REFUSAL