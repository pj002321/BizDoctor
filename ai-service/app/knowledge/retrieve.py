"""정책 문서 하이브리드 검색 (F-RAG-03).

risk_type 태그가 붙은 문서를 먼저 세우고, 모자라면 나머지 문서로 top_k 를 채운다
(스펙의 "필터 결과가 top_k 미만이면 전체 코퍼스 폴백"). 같은 그룹 안의 순서는
임베딩 코사인 순위와 키워드(fts) 순위를 RRF 로 합쳐 정한다. 두 점수는 범위가 달라
그냥 더할 수 없어서 순위만 쓴다.
"""

from sqlalchemy import text

from app.core.db import get_engine
from app.knowledge.embed import embed

# 질의임베딩(v), 질의 단어(k)러 믂은 검색식을 만들기 
# 임베딩 코사인 거리가 가까운 순서인 vec_rank, 다른 하나는 fts 키워드 점수가 높은 순서인 kw_rank로 합쳐 Score를 내서 정렬한다.
SEARCH = text("""
    WITH q AS (
        SELECT CAST(:embedding AS extensions.vector)      AS v,
               websearch_to_tsquery('simple', :keywords)   AS k
    ),
    ranked AS (
        SELECT d.doc_id, d.title, d.content, d.risk_type_tags,
               d.agency, d.target, d.limit_amount, d.rate, d.apply_period, d.url,
               rank() OVER (ORDER BY d.embedding <=> q.v)             AS vec_rank,
               rank() OVER (ORDER BY ts_rank(d.fts, q.k) DESC)         AS kw_rank
        FROM policy_doc d, q
    )
    SELECT *, 1.0 / (60 + vec_rank) + 1.0 / (60 + kw_rank) AS score
    FROM ranked
    ORDER BY coalesce(CAST(:risk_type AS text) = ANY(risk_type_tags), false) DESC, score DESC
    LIMIT :top_k
""")


def retrieve(query: str, risk_type: str | None = None, top_k: int = 3) -> list[tuple[dict, float]]:
    with get_engine().connect() as conn:
        rows = conn.execute(SEARCH, {
            "embedding": str(embed([query])[0]),
            "keywords": " or ".join(query.split()),  # 기본은 AND 라 문장 전체가 다 있어야 걸린다
            "risk_type": risk_type,
            "top_k": top_k,
        }).mappings().all()
    return [({k: v for k, v in r.items() if k not in ("score", "vec_rank", "kw_rank")}, float(r["score"]))
            for r in rows]


if __name__ == "__main__":
    # 태그가 붙은 문서가 있으면 1위는 반드시 그 태그를 달고 있어야 한다.
    for rt in ["고금리_과다채무형", "매출_폭락형", "상권_침체_붕괴형", "원가_상승_부담형", "단기_매출_정체형"]:
        hits = retrieve("소상공인 지원 제도", risk_type=rt)
        assert len(hits) == 3, rt
        assert rt in hits[0][0]["risk_type_tags"], (rt, hits[0][0]["doc_id"])
        print(rt, [d["doc_id"] for d, _ in hits])
    print("ok")
