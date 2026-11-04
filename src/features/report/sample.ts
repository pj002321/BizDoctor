import type { Signal } from "@/shared/types/signal";

/** 진단 없이 리포트 화면에 들어왔을 때 보여 주는 예시 결과. 화면에 "예시"라고 적는다. */
export const SAMPLE_SIGNAL: Signal = {
  risk_level: "YELLOW",
  risk_type: "단기_매출_정체형",
  risk_type_confidence: 0.65,
  score: 31,
  visual_theme: "yellow",
  solutions: [
    {
      source_doc_id: "POL_004",
      title: "일반경영안정자금 (소상공인 정책자금)",
      agency: "소상공인시장진흥공단",
      target: "업력 무관 소상공인",
      limit: "총 3조 3,620억원 규모 (개별 한도 확인 필요)",
      rate: "확인 필요",
      period: "2026년",
      summary:
        "임대료·인건비·재료비 같은 운전자금이 필요할 때 가장 먼저 검토할 자금입니다.",
    },
    {
      source_doc_id: "POL_007",
      title: "경영안정 바우처 및 디지털 전환 지원",
      agency: "소상공인시장진흥공단 · 지역 소상공인센터",
      target: "경쟁 심화·운영비 부담 소상공인",
      limit: "확인 필요",
      rate: "해당 없음 (바우처)",
      period: "2026년",
      summary:
        "POS·회계 프로그램 등 디지털 전환 도입과 무료 컨설팅을 지원합니다.",
    },
  ],
  level_probs: { GREEN: 0.41, YELLOW: 0.46, RED: 0.13 },
  type_probs: {
    정상_유지형: 0.41,
    단기_매출_정체형: 0.299,
    원가_상승_부담형: 0.161,
    매출_폭락형: 0.026,
    고금리_과다채무형: 0.059,
    상권_침체_붕괴형: 0.046,
  },
  low_confidence: true,
  sales_index: [100, 92.5, 81.1],
  place: {
    gu: "마포구",
    dong: "서교동",
    service: "커피-음료",
    industry: "숙박 및 음식점업",
  },
  percentile: 0.6,
  close_rate: 5,
  as_of: "2025 Q3",
};
