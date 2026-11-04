import "server-only";
import type { RiskType, Solution } from "@/shared/types/signal";

/**
 * 지원사업 문서 목업(F-RAG-01/02). ai-service/pipeline/doc/rag_documents.py 의 8건과 같은 문서다.
 * 본문에 없는 값은 "확인 필요"로 둔다 — 금액·금리·기간은 지어내면 사고다.
 * 실서비스 검색은 ai-service 의 retrieve(태그 우선 + 임베딩·키워드 RRF)가 한다.
 */
const NEED = "확인 필요";

const DOCS: (Solution & { tags: RiskType[] })[] = [
  {
    source_doc_id: "POL_001",
    title: "새출발기금 (채무조정)",
    tags: ["고금리_과다채무형"],
    agency: "한국자산관리공사(캠코) · 신용회복위원회",
    target: "3개월 이상 장기연체 등 상환이 어려운 개인사업자·법인 소상공인",
    limit: "담보 10억원, 무담보 5억원 (최대 15억원)",
    rate: "채무조정으로 금리부담 경감",
    period: "2026년 12월 말까지",
    summary:
      "상환기간 연장, 금리부담 완화, 상환이 어려운 차주는 원금조정까지 지원하는 채무조정 프로그램입니다.",
  },
  {
    source_doc_id: "POL_002",
    title: "신용회복위원회 채무조정 (장기연체자 특별채무조정)",
    tags: ["고금리_과다채무형"],
    agency: "신용회복위원회",
    target: "7년 이상 장기연체자",
    limit: "담보 10억원, 무담보 5억원 (최대 15억원)",
    rate: NEED,
    period: NEED,
    summary:
      "장기연체자 특별채무조정과 성실상환자 저금리 소액대출. 채권금융회사 다수결 절차가 필요합니다.",
  },
  {
    source_doc_id: "POL_003",
    title: "긴급경영안정자금 (2026년 중소기업 정책자금)",
    tags: ["매출_폭락형"],
    agency: "중소벤처기업부",
    target: "매출 급감·일시적 자금난 기업",
    limit: "총 2,500억원 규모 (개별 한도 확인 필요)",
    rate: NEED,
    period: "2026년",
    summary:
      "경영난을 겪는 기업의 운전자금을 신속히 지원합니다. 확인서 발급이 곧 대출 확정은 아닙니다.",
  },
  {
    source_doc_id: "POL_004",
    title: "일반경영안정자금 (소상공인 정책자금)",
    tags: ["원가_상승_부담형", "단기_매출_정체형"],
    agency: "소상공인시장진흥공단",
    target: "업력 무관 소상공인",
    limit: "총 3조 3,620억원 규모 (개별 한도 확인 필요)",
    rate: NEED,
    period: "2026년",
    summary:
      "임대료·인건비·재료비 같은 운전자금이 필요할 때 가장 먼저 검토할 자금입니다. 2026년부터 비대면 신청이 늘었습니다.",
  },
  {
    source_doc_id: "POL_005",
    title: "희망리턴패키지 (폐업 소상공인 재기지원)",
    tags: ["상권_침체_붕괴형"],
    agency: "소상공인시장진흥공단",
    target: "폐업 (예정) 소상공인",
    limit: NEED,
    rate: NEED,
    period: NEED,
    summary: "폐업 소상공인의 취업·재창업 프로그램을 연계합니다.",
  },
  {
    source_doc_id: "POL_006",
    title: "이차보전 사업 (금리 지원)",
    tags: ["고금리_과다채무형", "원가_상승_부담형"],
    agency: "중소벤처기업부",
    target: "민간 금융기관 대출을 보유한 중소벤처기업",
    limit: "총 3,670억원 규모",
    rate: "대출이자 일부 보전",
    period: "2026년",
    summary:
      "시중은행 대출을 유지하면서 이자 부담만 낮출 수 있어, 기존 대출이 있는 소상공인에게 맞습니다.",
  },
  {
    source_doc_id: "POL_007",
    title: "경영안정 바우처 및 디지털 전환 지원",
    tags: ["단기_매출_정체형", "원가_상승_부담형"],
    agency: "소상공인시장진흥공단 · 지역 소상공인센터",
    target: "경쟁 심화·운영비 부담 소상공인",
    limit: NEED,
    rate: "해당 없음 (바우처)",
    period: "2026년",
    summary:
      "POS·회계 프로그램 등 디지털 전환 도입과 지역 소상공인센터 무료 컨설팅을 지원합니다.",
  },
  {
    source_doc_id: "POL_008",
    title: "청년 소상공인 특화 자금",
    tags: ["단기_매출_정체형"],
    agency: "소상공인시장진흥공단",
    target: "만 39세 이하 청년 소상공인 또는 청년 고용 매장",
    limit: NEED,
    rate: "정책자금 기준금리 (변동)",
    period: "거치 2년 포함 5년 이내",
    summary:
      "업력이 짧아 자금 애로를 겪는 청년 소상공인의 초기 정착을 지원합니다.",
  },
];

/** 태그가 맞는 문서를 먼저 세우고, 모자라면 나머지로 채운다. 정상 유지형은 추천하지 않는다. */
export function findSolutions(type: RiskType, k = 3): Solution[] {
  if (type === "정상_유지형") return [];
  const tagged = DOCS.filter((d) => d.tags.includes(type));
  const rest = DOCS.filter((d) => !d.tags.includes(type));
  return [...tagged, ...rest].slice(0, k).map(({ tags: _t, ...s }) => s);
}
