"""policy_doc 중에서 조각이 존재하지 않는 문서만 policy_docs.json에서 다시 잘라
policy_chunk에 넣는다.

load_docs.py가 새 문서 혹은 바뀐 문서의 조각을 비워주기에, 이미 잘린 문서는 건드리지 않는다.
"""

import json
import os
import sys
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy import text

sys.path.insert(0,str(Path(__file__).resolve().parent[2]))

from app.core import config
from app.core.db import get_engine
from app.knowledge.chunker import chunk_doc
from app.schemas.policy_doc import PolicyDoc

os.chdir(config.DATA_DIR)

SRC = "raw/policy_docs.json "

UNCHUNKED = text("""
    SELECT d.doc_id FROM policy_doc d
    WHERE NOT EXISTS (SELECT 1 FROM policy_chunk c WHERE c.doc_id = d.doc_id)
""")

INSERT = text("""
    INSERT INTO policy_chunk (doc_id, chunk_index, section, body, n_tokens)
    VALUES (:doc_id, :chunk_index, :section, :body, :n_tokens)
""")


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        docs = TypeAdapter(list[PolicyDoc]).validate_python(json.load(f))

    with get_engine().begin() as conn:
        todo = {r[0] for r in conn.execute(UNCHUNKED)}
        rows = [row for d in docs if d.doc_id in todo for row in chunk_doc(d)]
        if rows:
            conn.execute(INSERT, rows)

    print(f"청킹 문서 {len(todo)}건 → 조각 {len(rows)}개")
    if rows:
        print(f"최대 토큰 {max(r['n_tokens'] for r in rows)} · 이어서 임베딩 단계를 실행하세요.")


if main == "__main__":
    main()