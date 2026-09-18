# -*- coding: utf-8 -*-
"""
상권 신호등 - RAG 파이프라인 (검색 → solutions 객체 생성)

흐름:
  1) rag_documents.py 의 지원제도 문서를 청크(문서 단위, 이미 짧아서 추가 분할 불필요) → 벡터화
  2) train_risk_model.py 가 예측한 risk_type을 쿼리로 사용해 최적 문서 검색
  3) 기획서에 정의된 solutions JSON 스키마로 변환

주의:
  - 지금은 디스크 용량 제약으로 TF-IDF(sklearn) 기반 검색을 사용함.
  - 실제 서비스에서는 기획서대로 sentence-transformers(ko-sbert) 또는
    상용 임베딩 API(OpenAI/Claude)로 교체하면 됨. 검색 인터페이스(retrieve 함수)는
    동일하게 유지되므로 교체 비용이 크지 않도록 설계함.
"""
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rag_documents import DOCUMENTS

# ------------------------------------------------------------------
# 1. 벡터 인덱스 구축
# ------------------------------------------------------------------
class SimpleRAGIndex:
    def __init__(self, documents):
        self.documents = documents
        self.vectorizer = TfidfVectorizer()
        corpus = [d["title"] + " " + d["content"] for d in documents]
        self.matrix = self.vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, risk_type: str = None, top_k: int = 3):
        """쿼리 텍스트 + risk_type 태그로 문서 검색.
        risk_type이 주어지면 해당 태그가 붙은 문서를 우선 후보로 좁힌 뒤 유사도 정렬."""
        candidates = self.documents
        if risk_type:
            tagged = [d for d in self.documents if risk_type in d["risk_type_tags"]]
            if tagged:
                candidates = tagged

        cand_idx = [self.documents.index(d) for d in candidates]
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.matrix[cand_idx]).flatten()
        ranked = sorted(zip(cand_idx, sims), key=lambda x: x[1], reverse=True)
        return [(self.documents[i], score) for i, score in ranked[:top_k]]


# ------------------------------------------------------------------
# 2. risk_type -> 검색 쿼리 문장 매핑 (실제로는 RAG 앞단에서 LLM이 상황 요약 후 쿼리 생성)
# ------------------------------------------------------------------
RISK_TYPE_QUERY = {
    "고금리_과다채무형": "대출 상환 부담이 크고 연체가 발생한 소상공인을 위한 채무조정 및 금리 지원 제도",
    "매출_폭락형": "매출이 급격히 감소해 긴급 운전자금이 필요한 소상공인 지원 제도",
    "상권_침체_붕괴형": "상권 침체로 폐업 위기에 놓인 소상공인의 재기 지원 제도",
    "원가_상승_부담형": "원재료비·인건비 상승으로 경영이 어려운 소상공인 지원 제도",
    "단기_매출_정체형": "동일업종 경쟁 심화, 임대료 부담으로 매출이 정체된 소상공인 지원 제도",
    "정상_유지형": None,
}

RISK_TYPE_TO_LEVEL = {
    "정상_유지형": ("GREEN", "#2ECC71", "건전하게 운영되고 있습니다"),
    "단기_매출_정체형": ("YELLOW", "#F1C40F", "⚠️ 자금 흐름 모니터링이 필요합니다"),
    "원가_상승_부담형": ("YELLOW", "#F1C40F", "⚠️ 원가 부담이 커지고 있습니다"),
    "매출_폭락형": ("RED", "#FF2B2B", "🚨🚨 3개월 내 심각한 자금난 발생 위험! (경고)"),
    "고금리_과다채무형": ("RED", "#FF2B2B", "🚨🚨 대출 상환 부담이 위험 수준입니다 (경고)"),
    "상권_침체_붕괴형": ("RED", "#FF2B2B", "🚨🚨 상권 침체로 폐업 위험이 높습니다 (경고)"),
}

ACTION_TYPE_MAP = {
    "새출발기금 (채무조정)": ("APPLY_NOW", "채무조정 즉시 신청하기"),
    "신용회복위원회 채무조정 (장기연체자 특별채무조정)": ("APPLY_NOW", "채무조정 상담 신청하기"),
    "긴급경영안정자금 (2026년 중소기업 정책자금)": ("APPLY_NOW", "긴급자금 신청하기"),
    "일반경영안정자금 (소상공인 정책자금)": ("LINK_GUIDE", "지원 대상 자격 확인하기"),
    "희망리턴패키지 (폐업 소상공인 재기지원)": ("LINK_GUIDE", "재기지원 프로그램 안내받기"),
    "이차보전 사업 (금리 지원)": ("LINK_GUIDE", "이차보전 대상 확인하기"),
    "경영안정 바우처 및 디지털 전환 지원": ("LINK_GUIDE", "바우처 신청 방법 보기"),
    "청년 소상공인 특화 자금": ("LINK_GUIDE", "청년 특화자금 안내받기"),
}


# ------------------------------------------------------------------
# 3. solutions JSON 객체 생성 (기획서 3번 스키마와 동일 구조)
# ------------------------------------------------------------------
def build_signal_json(company_id: str, risk_type: str, score: float, index: SimpleRAGIndex):
    level, bg_color, message = RISK_TYPE_TO_LEVEL[risk_type]
    query = RISK_TYPE_QUERY[risk_type]

    solutions = []
    if query:
        # top_k 2 → 3 상향 (2026-08-19)
        #   TF-IDF 는 문서 길이로 정규화되므로, 제도 설명이 길수록 순위가 밀린다.
        #   고금리_과다채무형에서 새출발기금(445자)이 3위로 잘려 30,000건 중 추천 0회였다.
        #   핵심어 등장 횟수는 1위 문서와 동일한 13회였으나 밀도가 5.49% → 2.92% 로 희석됨.
        #   태그당 문서가 최대 3건이므로 3으로 올리면 후보 전체를 노출한다.
        #   근본 해결은 ko-sbert 등 의미 기반 임베딩으로의 교체.
        results = index.retrieve(query, risk_type=risk_type, top_k=3)
        for doc, sim in results:
            action_type, action_label = ACTION_TYPE_MAP.get(
                doc["title"], ("LINK_GUIDE", "자세히 알아보기")
            )
            solutions.append({
                "solution_id": doc["doc_id"],
                "title": doc["title"],
                "description": doc["content"][:80] + "...",
                "action_type": action_type,
                "action_button_label": action_label,
                "_similarity_score": round(float(sim), 3),  # 디버깅용, 실서비스에서는 제거
            })

    return {
        "company_id": company_id,
        "risk_level": level,
        "score": round(float(score), 1),
        "visual_theme": {
            "bg_color": bg_color,
            "animation": "pulse_warning" if level == "RED" else (
                "blink_caution" if level == "YELLOW" else "soft_glow"
            ),
            "impact_message": message,
        },
        "risk_type": risk_type,
        "solutions": solutions,
    }


# ------------------------------------------------------------------
# 4. 데모 실행
# ------------------------------------------------------------------
if __name__ == "__main__":
    index = SimpleRAGIndex(DOCUMENTS)

    demo_cases = [
        ("SGB_000099", "고금리_과다채무형", 78.5),
        ("SGB_000123", "매출_폭락형", 65.2),
        ("SGB_000456", "상권_침체_붕괴형", 82.0),
        ("SGB_000789", "원가_상승_부담형", 34.0),
        ("SGB_001000", "단기_매출_정체형", 28.5),
    ]

    for company_id, risk_type, score in demo_cases:
        result = build_signal_json(company_id, risk_type, score, index)
        print(f"\n{'='*60}")
        print(json.dumps(result, ensure_ascii=False, indent=2))