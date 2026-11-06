from app.graph.nodes import grade_docs, route_after_grade

SIGNAL = {"risk_level": "RED", "risk_type": "매출_폭락형", "risk_type_confidence": 0.6, "score": 30}


def _doc(i, tags):
    return {"doc_id": i, "title": f"공고{i}", "agency": "기관", "source_url": "u",
            "section": "지원대상", "evidence": "e", "risk_type_tags": tags}


def test_태그_불일치는_재검색으로():
    state = {"signal": SIGNAL, "docs": [(_doc(1, ["고금리_과다채무형"]), 0.03)]}
    state |= grade_docs(state)
    assert state["docs"] == [] and route_after_grade(state) == "rewrite_query"


def test_relaxed_는_태그없는_공고도_남기고_빈결과면_종료():
    state = {"signal": SIGNAL, "relaxed": True, "docs": [(_doc(1, None), 0.03)]}
    state |= grade_docs(state)
    assert len(state["docs"]) == 1 and route_after_grade(state) == "generate"
    assert route_after_grade({**state, "docs": []}) == "no_docs"