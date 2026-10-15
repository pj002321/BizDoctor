# -*- coding: utf-8 -*-
"""
상권 신호등 - RAG 파이프라인 (검색 → solutions 객체 생성)

흐름:
  1) rag_documents.py 의 지원제도 문서를 청크(문서 단위, 이미 짧아서 추가 분할 불필요) → 벡터화
  2) train_risk_model.py 가 예측한 risk_type을 쿼리로 사용해 최적 문서 검색
  3) 기획서에 정의된 solutions JSON 스키마로 변환

검색은 app/knowledge/retrieve.py (임베딩 + 키워드 하이브리드) 가 한다.
먼저 build_index.py 로 policy_doc 을 채워야 한다.
"""
import json
from app.domain.signal import RISK_TYPE_QUERY, build_signal
from app.knowledge.retrieve import retrieve

# ------------------------------------------------------------------
# 1. 검색 — 문서는 policy_doc(Postgres)에 있다. 색인은 build_index.py 가 만든다.
# ------------------------------------------------------------------
class SimpleRAGIndex:
    def retrieve(self, query: str, risk_type: str = None, top_k: int = 3):
        return retrieve(query, risk_type, top_k)


# ------------------------------------------------------------------
# 2. 신호 JSON — 계약 모양은 app/domain/signal.py 가 정한다.
# ------------------------------------------------------------------
def build_signal_json(risk_type: str, confidence: float, score: float, index: SimpleRAGIndex):
    query = RISK_TYPE_QUERY[risk_type]
    docs = [d for d, _ in index.retrieve(query, risk_type=risk_type, top_k=3)] if query else []
    return build_signal(risk_type, confidence, score, docs)


# ------------------------------------------------------------------
# 3. 데모 실행
# ------------------------------------------------------------------
if __name__ == "__main__":
    index = SimpleRAGIndex()

    demo_cases = [
        ("고금리_과다채무형", 0.61, 78.5),
        ("매출_폭락형", 0.42, 65.2),
        ("상권_침체_붕괴형", 0.38, 82.0),
        ("원가_상승_부담형", 0.35, 34.0),
        ("단기_매출_정체형", 0.47, 28.5),
    ]

    for risk_type, confidence, score in demo_cases:
        result = build_signal_json(risk_type, confidence, score, index)
        print(f"\n{'='*60}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
