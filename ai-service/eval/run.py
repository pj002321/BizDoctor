"""검색 모드별로 골든셋을 채점해 표로 출력한다.

python -m eval.run # mode all
python -m eval.run --modes rrf rrf_tag # mode select
"""

import argparse
import json
from datetime import date
from statistics import mean

from app.knowledge.retrieve import MODES, retrieve
from eval.golden import AS_OF, POLICY_DOCS, load_golden
from eval.metrics import expired_shown, hit_at_k, reciprocal_rank

def expired_ids() -> set[str]:
    """AS_OF 기준 마감된 공고로 검색 결과에 하나라도 섞이면 안된다."""
    docs = json.loads(POLICY_DOCS.read_text(encoding="utf-8"))
    return {d["doc_id"] for d in docs if d["apply_end"] and date.fromisoformat(d["apply_end"]) < AS_OF}


def score(mode: str, items, expired: set[str]) -> tuple[float,float,float]:
    hits, rrs, leaks = [],[],[]
    for item in items:
        ids = [d["doc_id"] for d, _ in retrieve(item.question, risk_type=item.risk_type,mode=mode,as_of=AS_OF)]

        leaks.append(expired_shown(ids, expired))
        if item.gold_doc_ids:
            hits.append(hit_at_k(ids, item.gold_doc_ids))
            rrs.append(reciprocal_rank(ids, item.gold_doc_ids))
    return mean(hits), mean(rrs), mean(leaks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes",nargs="+", choices=list(MODES), default=list(MODES))
    args = parser.parse_args()

    items, expired = load_golden(), expired_ids()
    print(f"기준일 {AS_OF} | 문항 {len(items)} (정답 있는 문항 {sum(bool(i.gold_doc_ids) for i in items)})")
    print("| mode | hit@3 | MRR | 마감 노출 |")
    print("|---|---|---|---|")
    for mode in args.modes:
        h, r, e = score(mode, items, expired)
        print(f"| {mode} | {h:.2f} | {r:.2f} | {e:.2f} |")