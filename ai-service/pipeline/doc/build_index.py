"""policy_chunk 중 임베딩이 비어 있는 조각만 OpenAI 로 임베딩해 채운다.

묶음(EMBED_BATCH_SIZE)마다 commit 하므로 중간에 끊겨도 다시 돌리면 남은 조각부터 잇는다.
모델을 바꾸면 이전 모델 벡터를 비운다 — 다른 모델 벡터끼리는 비교가 안 된다.
"""

import os
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.core import config
from app.core.db import get_engine
from app.knowledge.embed import embed

os.chdir(config.DATA_DIR)

RESET_STALE = text("""
    UPDATE policy_chunk SET embedding = NULL, embedding_model = NULL
    WHERE embedding_model <> :model
""")

PENDING = text("SELECT id, body FROM policy_chunk WHERE embedding IS NULL ORDER BY id")

FILL = text("""
    UPDATE policy_chunk
    SET embedding = CAST(:embedding AS extensions.vector), embedding_model = :model
    WHERE id = :id
""")

def main() -> None:
    engine = get_engine()
    with engine.begin() as conn:    # 비우기와 목록 조회를 동시에 해서 재임베딩
        stale = conn.execute(RESET_STALE, {"model": config.EMBED_MODEL}).rowcount
        pending = conn.execute(PENDING).all()       

    size = config.EMBED_BATCH_SIZE
    for start in range(0, len(pending),size):
        batch = pending[start:start + size]
        vectors = embed([body for _, body in batch])
        with engine.begin() as conn:    # 임베딩 호출은 트랜잭션 밖에서 -> OpenAI응답 동안 DB연결을 붙잡지 않음.
            conn.execute(FILL, [
                {"id": cid, "embedding": str(v), "model": config.EMBED_MODEL}   # pgvector 처리
                for (cid, _), v in zip(batch,vectors,strict=True)               # 보낸 조각 수와 받은 벡터 수가 다르면 오류
            ])

        print(f"임베딩 {min(start + size, len(pending))}/{len(pending)}")
    
    print(f"완료 — 모델 변경으로 비운 조각 {stale}개 · 새로 임베딩한 조각 {len(pending)}개")


if __name__ == "__main__":
    main()

