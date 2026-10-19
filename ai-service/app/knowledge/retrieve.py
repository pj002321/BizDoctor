"""정책 문서 하이브리드 검색.

마감된 공고 제외 → risk_type 태그가 붙은 공고를 먼저 → 조각마다 벡터 순위와
키워드 순위를 RRF 로 합침 → 공고마다 가장 잘 맞는 조각 하나만 남긴다.
두 점수는 범위가 달라 그냥 더할 수 없어서 순위만 쓴다.
"""

from sqlalchemy import text

from app.core.db import get_engine
from app.knowledge.embed import embed

# RRF 상수. 순위 1위와 10위의 차이를 완만하게 만든다. 논문 기본값.
RRF_K = 60

# 조각 단위로 두 순위를 매겨 합치고(scored), 공고마다 1등 조각만 남긴 뒤(best),
# 태그 일치 → 점수 순으로 자른다. 키워드가 하나도 안 맞는 조각은 키워드 점수 0.
SEARCH = text("""
    WITH q AS (
        SELECT CAST(:embedding AS extensions.vector)    AS v,
               websearch_to_tsquery('simple', :keywords) AS k
    ),
    active AS (
        SELECT * FROM policy_doc
        WHERE apply_end IS NULL OR apply_end >= (now() AT TIME ZONE 'Asia/Seoul')::date
    ),
    scored AS (
        SELECT c.doc_id, c.section, c.body,
               1.0 / (:rrf_k + rank() OVER (ORDER BY c.embedding <=> q.v))
             + CASE WHEN c.fts @@ q.k
                    THEN 1.0 / (:rrf_k + rank() OVER (ORDER BY ts_rank(c.fts, q.k) DESC))
                    ELSE 0 END AS score
        FROM policy_chunk c JOIN active a USING (doc_id), q
        WHERE c.embedding IS NOT NULL
    ),
    best AS (
        SELECT DISTINCT ON (doc_id) * FROM scored ORDER BY doc_id, score DESC
    )
    SELECT a.doc_id, a.title, a.agency, a.source_url, a.limit_text, a.rate_text,
           a.apply_start, a.apply_end, a.risk_type_tags, b.section, b.body AS evidence, b.score
    FROM best b JOIN active a USING (doc_id)
    ORDER BY coalesce(CAST(:risk_type AS text) = ANY(a.risk_type_tags), false) DESC, b.score DESC
    LIMIT :top_k
""")



def retrieve(query: str, risk_type: str | None = None, top_k: int = 3) -> list[tuple[dict, float]]:
    """질의와 진단 유형으로 접수 중인 공고 top_k 개를 고른다. 공고마다 가장 잘 맞는 조각 하나가 근거로 붙는다.
    """

    with get_engine().connect() as conn:
        rows = conn.execute(SEARCH, {
            "embedding": str(embed([query])[0]),
            "keywords": " or ".join(query.split()),  # 기본은 AND 라 문장 전체가 다 있어야 걸린다
            "risk_type": risk_type,
            "top_k": top_k,
            "rrf_k": RRF_K,
        }).mappings().all()
    return [({k: v for k, v in r.items() if k != "score"}, float(r["score"])) for r in rows]



if __name__ == "__main__":
    # DB 에 적재·청킹·임베딩이 끝난 뒤 돌린다. 1위는 태그가 맞아야 하고, 마감 공고는 절대 안 나온다.
    expired = "semas-2026-smartstore-2"  # 2026-09-30 마감
    for rt in ["고금리_과다채무형", "매출_폭락형", "상권_침체_붕괴형", "원가_상승_부담형", "단기_매출_정체형"]:
        hits = retrieve("소상공인 지원 제도", risk_type=rt)
        ids = [d["doc_id"] for d, _ in hits]
        assert rt in hits[0][0]["risk_type_tags"], (rt, ids)
        assert expired not in ids, (rt, ids)
        assert len(ids) == len(set(ids)), ids
        print(rt, ids)
    print("ok")