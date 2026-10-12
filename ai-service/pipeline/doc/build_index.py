"""정책 문서를 임베딩해 policy_doc 에 넣는다 (F-RAG-01).

doc_id 로 upsert(update(값이 존재할 때)+insert(값이 없을때)) 하므로 몇 번을 다시 돌려도 결과가 같다.
"""

from sqlalchemy import create_engine, text

from app.core.config import DATABASE_URL
from app.knowledge.embed import embed
from rag_documents import DOCUMENTS

# policy_doc 테이블에 각 5가지 컬럼 값을 insert한다. 벡터는 pgvector타입으로 캐스팅한다.
# doc_id에 대한 PK 충돌이 날 경우, 오류를 산출하지 않고 기존 행의 컬럼을 새 값으로 바꾼다.
UPSERT = text("""
    INSERT INTO policy_doc (doc_id, title, content, risk_type_tags, embedding)                      
    VALUES (:doc_id, :title, :content, :risk_type_tags, CAST(:embedding AS extensions.vector))
    ON CONFLICT (doc_id) DO UPDATE SET
        title          = EXCLUDED.title,
        content        = EXCLUDED.content,
        risk_type_tags = EXCLUDED.risk_type_tags,
        embedding      = EXCLUDED.embedding
""")

# ponytail: 한 번에 전부 임베딩. 문서가 EMBED_BATCH_SIZE(100) 를 넘으면 나눠 보낸다.
vectors = embed([d["title"] + " " + d["content"] for d in DOCUMENTS])

rows = [
    {
        "doc_id": d["doc_id"],
        "title": d["title"],
        "content": d["content"],
        "risk_type_tags": d["risk_type_tags"],
        "embedding": str(v),
    }
    for d, v in zip(DOCUMENTS, vectors)
]

with create_engine(DATABASE_URL).begin() as conn:
    conn.execute(UPSERT, rows)

print(f"policy_doc {len(rows)}건 upsert")
