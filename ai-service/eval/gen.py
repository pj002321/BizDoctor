"""골든셋 질문에 실제로 답하게 하고 생성 지표를 낸다.

OPENAI_MODEL 필요. ANTHROPIC_API_KEY 가 있으면 근거 충실도까지 잰다.
python -m eval.gen
"""

import re
from statistics import mean

from app.ai.answer import REFUSAL, answer
from app.core.config import ANTHROPIC_API_KEY
from app.domain.guardrail import check
from app.domain.report_context import docs_context
from app.knowledge.retrieve import retrieve
from eval.golden import AS_OF, load_golden


def _squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


if __name__ == "__main__":
    if ANTHROPIC_API_KEY:
        from app.ai.verify import verify

    facts, refusals, clean, faithful = [], [], [], []
    for item in load_golden():
        docs = [d for d, _ in retrieve(item.question, risk_type=item.risk_type, as_of=AS_OF)]
        ctx = docs_context(docs)
        text = answer(item.question, ctx)
        refused = REFUSAL in text

        refusals.append(refused == (not item.gold_doc_ids))  # 정답 없으면 거절이 맞고, 있으면 답하는 게 맞다
        if item.gold_facts:
            # ponytail: 띄어쓰기만 무시한 글자 포함 — "25만원" 처럼 줄여 쓰면 놓친다. 오탐이 많으면 숫자만 대조로
            facts.append(not refused and all(_squash(f.value) in _squash(text) for f in item.gold_facts))
        if not refused:
            clean.append(not check(text, ctx))
            if ANTHROPIC_API_KEY:
                claims, bad = verify(text, ctx)
                faithful.append(1 - len(bad) / len(claims) if claims else 1.0)

        print(f"[{item.id} · {item.type}] {'거절' if refused else '답변'} {'✓' if refusals[-1] else '✗'} | {text[:80]}")

    print()
    print("| 지표 | 값 |")
    print("|---|---|")
    print(f"| 거절 정확도 | {mean(refusals):.2f} |")
    print(f"| 정답 사실 포함률 | {mean(facts):.2f} |")
    print(f"| 가드레일 통과율 | {mean(clean):.2f} |")
    print(f"| 근거 충실도 | {f'{mean(faithful):.2f}' if faithful else '-'} |")