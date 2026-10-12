"""진단 결과 + 검색된 정책 문서 → 프론트 계약 신호 JSON (F-RAG-04).

DB·모델 없이 돈다. 검색은 호출하는 쪽이 해서 문서만 넘긴다.
"""

from textwrap import shorten

RISK_TYPE_TO_LEVEL = {
    "정상_유지형": "GREEN",
    "단기_매출_정체형": "YELLOW",
    "원가_상승_부담형": "YELLOW",
    "매출_폭락형": "RED",
    "고금리_과다채무형": "RED",
    "상권_침체_붕괴형": "RED",
}

# 검색 질의 문장. 정상_유지형은 추천할 지원사업이 없어 검색하지 않는다.
RISK_TYPE_QUERY = {
    "고금리_과다채무형": "대출 상환 부담이 크고 연체가 발생한 소상공인을 위한 채무조정 및 금리 지원 제도",
    "매출_폭락형": "매출이 급격히 감소해 긴급 운전자금이 필요한 소상공인 지원 제도",
    "상권_침체_붕괴형": "상권 침체로 폐업 위기에 놓인 소상공인의 재기 지원 제도",
    "원가_상승_부담형": "원재료비·인건비 상승으로 경영이 어려운 소상공인 지원 제도",
    "단기_매출_정체형": "동일업종 경쟁 심화, 임대료 부담으로 매출이 정체된 소상공인 지원 제도",
    "정상_유지형": None,
}


def build_signal(risk_type: str, confidence: float, score: float, docs: list[dict]) -> dict:
    level = RISK_TYPE_TO_LEVEL[risk_type]
    return {
        "risk_level": level,
        "risk_type": risk_type,
        "risk_type_confidence": round(confidence, 2),
        "score": round(score),
        "visual_theme": level.lower(),
        "solutions": [
            {
                "title": d["title"],
                "agency": d.get("agency"),
                "summary": shorten(d["content"], 80, placeholder="…"),
                "limit": d.get("limit_amount"),
                "rate": d.get("rate"),
                "url": d.get("url"),
                "source_doc_id": d["doc_id"],
            }
            for d in docs
        ],
    }


if __name__ == "__main__":
    assert RISK_TYPE_TO_LEVEL.keys() == RISK_TYPE_QUERY.keys()

    doc = {"doc_id": "POL_001", "title": "새출발기금", "content": "가" * 200, "agency": "캠코"}
    s = build_signal("고금리_과다채무형", 0.613, 32.4, [doc])
    assert s["risk_level"] == "RED" and s["visual_theme"] == "red"
    assert s["risk_type_confidence"] == 0.61 and s["score"] == 32
    sol = s["solutions"][0]
    assert sol.keys() == {"title", "agency", "summary", "limit", "rate", "url", "source_doc_id"}
    assert len(sol["summary"]) <= 80

    assert build_signal("정상_유지형", 0.9, 0, [])["solutions"] == []
    print("ok")
