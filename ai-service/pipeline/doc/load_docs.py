"""policy_docs.json → policy_doc.

자르지도, 임베딩하지도 않는다. 본문이 바뀐 문서는 조각을 지워 두고, 청킹 단계가
조각 없는 문서를 다시 자른다. JSON 에서 사라진 문서는 지운다(조각은 cascade).
"""

import hashlib
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent[2]))
from app.core import config 
from app.core.db import get_engine
from app.domain.signal import RISK_TYPE_QUERY
from app.schemas.policy_doc import PolicyDoc

os.chdir(config.DATA_DIR)

SRC = "raw/policy_docs.json"

UPSERT = text("""
    INSERT INTO policy_doc (doc_id, title, agency, source_uurl, apply_start, apply_end, limit_text, rate_text, risk_type_tags, content_hash)
    VALUES (:doc_id, :title, :agency, :source_url, :apply_start, :apply_end, :limit_text, :rate_text, :risk_type_tags, :content_hash)
    ON CONFLICT (doc_id) DO UPDATE SET
        title = EXCLUDED.title,
        agency = EXCLUDED.agency,
        source_url = EXCLUDED.source_url,
        apply_start = EXCLUDED.apply_start, 
        apply_end = EXCLUDED.apply_end,
        limit_text = EXCLUDED.limit_text,
        rate_text = EXCLUDED.rate_text,
        risk_type_tags = EXCLUDED.risk_type_tags,
        content_hash = EXCLUDED.content_hash,
        updated_at = now()
    WHERE (
        policy_doc.title,
        policy_doc.agency,
        policy_doc.source_url,
        policy_doc.apply_start,
        policy_doc.apply_end,
        policy_doc.limit_text,
        policy_doc.rate_text,
        policy_doc.risk_type_tags,
        policy_doc.content_hash)
    IS DISTINCT FROM (
        EXCLUDED.title,
        EXCLUDED.agency,
        EXCLUDED.source_url,
        EXCLUDED.apply_start,
        EXCLUDED.apply_end,
        EXCLUDED.limit_text,
        EXCLUDED.rate_text,
        EXCLUDED.risk_type_tags,
        EXCLUDED.content_hash)
""")

DELETE_CHUNKS = text("DELETE FROM policy_chunk WHERE doc_id = ANY(:ids)")
DELETE_DOCS = text("DELETE FROM policy_doc WHERE doc_id = ANY(:ids)")

def content_hash(doc: PolicyDoc) -> str:
    """조각 본문을 만드는 값(제목 · 항목)만 해시한다. 한도,마감일만 바뀌면 다시 자를 필요가 없다."""

    payload = json.dumps(
        {"title": doc.title, "sections": [s.model_dump() for s in doc.sections]},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check_docs(docs: list[PolicyDoc], today: date) -> None:
    """문서 묶음 전체를 봐야 하는 검사. doc_id 중복, 접수 중인 문서가 없는 risk_type 이 있으면 ValueError. 
    today 는 테스트에서 날짜를 고정하려고 인자로 받는다."""

    dup = [k for k, n in Counter(d.doc_id for d in docs).items() if n > 1]
    if dup:
        raise ValueError(f"doc_id 중복: {dup}")

    # 접수 중인 문서로만 센다. 마감된 문서만 남은 유형은 검색에서 빈값이 된다.
    active = [d for d in docs if d.apply_end is None or d.apply_end >= today]
    counts = Counter(tag for d in active for tag in d.risk_type_tags)
    missing = [rt for rt, query in RISK_TYPE_QUERY.items() if query and counts[rt] == 0]
    if missing:
        raise ValueError(f"접수 중인 문서가 없는 risk_type: {missing}")

def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        docs = TypeAdapter(list[PolicyDoc]).validate_python(json.load(f))
    check_docs(docs, date.today())

    rows = [
        {**d.model_dump(exclude={"sections"}), "content_hash": content_hash(d)}
        for d in docs
    ]

    with get_engine().begin() as conn:
        existing = dict(conn.execute(text("SELECT doc_id, content_hash FROM policy_doc")).all())
        new = [r["doc_id"] for r in rows if r["doc_id"] not in existing]
        changed = [r["doc_id"] for r in rows
                   if r["doc_id"] in existing and existing[r["doc_id"]] != r["content_hash"]]
        removed = sorted(existing.keys() - {r["doc_id"] for r in rows})

        if changed:
            conn.execute(DELETE_CHUNKS, {"ids": changed})
        if removed:
            conn.execute(DELETE_DOCS, {"ids": removed})
        conn.execute(UPSERT, rows)

    print(f"policy_doc 전체 {len(rows)}건 — 추가 {len(new)} · 본문 변경 {len(changed)} · 삭제 {len(removed)}")
    if new or changed:
        print("본문이 바뀐 문서가 있습니다. 이어서 청킹 단계를 실행하세요.")


if __name__ == "__main__":
    main()