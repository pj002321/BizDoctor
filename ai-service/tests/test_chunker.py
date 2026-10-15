import pytest

from app.knowledge.chunker import MAX_TOKENS, chunk_doc, count_tokens, split_section
from app.schemas.policy_doc import PolicyDoc

def _doc(**sections: str) -> PolicyDoc:
    return PolicyDoc(
        doc_id="t-1", title="테스트제도", agency="중기부", source_url="https://x.kr",
        risk_type_tags=["매출_폭락형"],
        sections=[{"name": k, "body": v} for k, v in sections.items()],
    )


def test_짧은_항목은_머리말_붙은_조각_하나():
    rows = chunk_doc(_doc(지원대상="개인사업자", 지원한도="최대 7천만원"))
    assert [r["chunk_index"] for r in rows] == [0, 1]
    assert rows[0]["body"] == "[테스트제도 · 지원대상] 개인사업자"
    assert rows[1]["section"] == "지원한도"


def test_긴_항목은_문장_경계에서_나뉘고_모두_한도_이하():
    body = "\n".join(f"{i}번 조건을 충족하는 소상공인은 신청할 수 있다." for i in range(200))
    rows = chunk_doc(_doc(지원대상=body))
    assert len(rows) > 1
    assert all(r["body"].startswith("[테스트제도 · 지원대상] ") for r in rows)
    assert all(r["n_tokens"] == count_tokens(r["body"]) <= MAX_TOKENS for r in rows)
    assert [r["chunk_index"] for r in rows] == list(range(len(rows)))


def test_한도를_넘는_한_문장은_오류():
    with pytest.raises(ValueError, match="토큰을 넘는다"):
        split_section("[테스트제도 · 지원대상]", "가" * 3000)