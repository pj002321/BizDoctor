"""챗봇 도구 루프: OpenAI 대신 정해진 응답을 차례로 내는 가짜를 끼운다."""

# 테스트 4개는 상황 4개

# ┌────────────────────────────────┬────────────────────────────┬───────────────────────────────────┐
# │             테스트             │     대역에게 시킨 상황     │     감수 창구가 해야 할 판정      │
# ├────────────────────────────────┼────────────────────────────┼───────────────────────────────────┤
# │                                │ 답에 「대환대출」만 나옴,  │ 답을 그대로 내보내고, 출처는 d1   │
# │ 통과하면_답에_나온_공고만_출처 │ 위반 없음                  │ 하나만 남김(바우처는 답에 없으니  │
# │                                │                            │ 뺌)                               │
# ├────────────────────────────────┼────────────────────────────┼───────────────────────────────────┤
# │                                │ 숫자 검사원이 "비율 3%는   │ 답 대신 CHECK_FAILED 안내를       │
# │ 숫자가_근거에_없으면_원문_안내 │ 근거에 없음"이라고 보고    │ 내보내고, 출처 2건은 전부 남겨    │
# │                                │                            │ 원문 링크로 쓰게 함               │
# ├────────────────────────────────┼────────────────────────────┼───────────────────────────────────┤
# │                                │ 숫자는 통과, Claude가      │                                   │
# │ 주장이_근거에_없어도_원문_안내 │ "누구나 됩니다"를 걸었다고 │ 이번에도 check_failed             │
# │                                │  보고                      │                                   │
# ├────────────────────────────────┼────────────────────────────┼───────────────────────────────────┤
# │ 거절은_검사_없이_그대로        │ 작성자가 "해당하는 접수 중 │ 검사 없이 거절을 그대로 내보냄    │
# │                                │  공고가 없습니다"라고 씀   │                                   │
# └────────────────────────────────┴────────────────────────────┴───────────────────────────────────┘
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



SRC = [{"docId": "d1", "title": "대환대출"}, {"docId": "d2", "title": "바우처"}]

# _stub: 대역 직원 세 명을 세우는 함수
def _stub(monkeypatch, answer, bad_numbers=(), bad_claims=()):
    monkeypatch.setattr(c, "chat", lambda m, h, t: (answer, "근거", SRC))
    monkeypatch.setattr(c, "check", lambda a, ctx: list(bad_numbers))
    monkeypatch.setattr(c, "verify", lambda a, ctx: ([], list(bad_claims)))


def test_통과하면_답에_나온_공고만_출처(monkeypatch):
    _stub(monkeypatch, "「대환대출」은 연 4.5%입니다.")
    assert c.checked_chat("?", [], {}) == ("「대환대출」은 연 4.5%입니다.", [SRC[0]], "passed")


def test_숫자가_근거에_없으면_원문_안내(monkeypatch):
    _stub(monkeypatch, "「대환대출」은 연 3%입니다.", bad_numbers=["비율 3%"])
    answer, sources, outcome = c.checked_chat("?", [], {})
    assert (answer, outcome) == (c.CHECK_FAILED, "check_failed") and sources == SRC


def test_주장이_근거에_없어도_원문_안내(monkeypatch):
    _stub(monkeypatch, "「대환대출」은 누구나 됩니다.", bad_claims=["누구나 됩니다"])
    assert c.checked_chat("?", [], {})[2] == "check_failed"


def test_거절은_검사_없이_그대로(monkeypatch):
    _stub(monkeypatch, c.REFUSAL)
    monkeypatch.setattr(c, "verify", lambda a, ctx: 1 / 0)  # 불리면 터짐
    assert c.checked_chat("?", [], {}) == (c.REFUSAL, [], "refused")
