/**
 * 정책자금 문서 코퍼스 (F-RAG-01/02) — src/rag_documents.py 의 8건을 옮기고 메타데이터 필드를 추가.
 * 메타데이터는 본문에 적힌 값만 채웠고, 본문에 없는 값은 '확인 필요'로 둠 (수기 태깅·검수 대상).
 */
import type { RiskType, Solution } from './types';

export interface PolicyDoc {
  docId: string;
  title: string;
  riskTypeTags: RiskType[];
  agency: string;
  target: string;
  limit: string;
  rate: string;
  period: string;
  url: string;          // 공고 URL — 아직 미등록
  content: string;
  actionType: 'APPLY_NOW' | 'LINK_GUIDE';
  actionLabel: string;
  updatedAt: string;
}

const NEED = '확인 필요';

export const POLICY_DOCS: PolicyDoc[] = [
  {
    docId: 'POL_001', title: '새출발기금 (채무조정)', riskTypeTags: ['고금리_과다채무형'],
    agency: '한국자산관리공사(캠코) · 신용회복위원회', target: '2020.4~2025.6 사업 운영 개인사업자·법인 소상공인 (3개월 이상 장기연체 등)',
    limit: '담보 10억원, 무담보 5억원 (최대 15억원)', rate: '채무조정으로 금리부담 경감', period: '2026년 12월 말까지', url: '',
    content: '코로나19 이후 대출 상환이 어려워진 자영업자·소상공인의 채무조정 프로그램. 상환기간 연장, 금리부담 완화, 상환이 어려운 차주는 원금조정 지원. 새출발기금 홈페이지 또는 캠코 지역본부·서민금융통합지원센터에서 신청.',
    actionType: 'APPLY_NOW', actionLabel: '채무조정 즉시 신청하기', updatedAt: '2026-08-19',
  },
  {
    docId: 'POL_002', title: '신용회복위원회 채무조정 (장기연체자 특별채무조정)', riskTypeTags: ['고금리_과다채무형'],
    agency: '신용회복위원회', target: '7년 이상 장기연체자', limit: '담보 10억원, 무담보 5억원 (최대 15억원)', rate: NEED, period: NEED, url: '',
    content: '7년 이상 장기연체자 특별채무조정, 성실상환자 대상 저금리 소액대출. 채권금융회사 다수결 절차가 필요하며 부결 시 연체·추심이 재개될 수 있음.',
    actionType: 'APPLY_NOW', actionLabel: '채무조정 상담 신청하기', updatedAt: '2026-08-19',
  },
  {
    docId: 'POL_003', title: '긴급경영안정자금 (2026년 중소기업 정책자금)', riskTypeTags: ['매출_폭락형'],
    agency: '중소벤처기업부', target: '매출 급감·일시적 자금난 기업', limit: '총 2,500억원 규모 (개별 한도 확인 필요)', rate: NEED, period: '2026년', url: '',
    content: '경영난을 겪는 기업이 신속히 운전자금을 확보할 수 있도록 지원. 은행·보증기관 심사 단계에서 최종 대출이 거절될 수 있어 확인서 발급이 곧 대출 확정은 아님.',
    actionType: 'APPLY_NOW', actionLabel: '긴급자금 신청하기', updatedAt: '2026-08-19',
  },
  {
    docId: 'POL_004', title: '일반경영안정자금 (소상공인 정책자금)', riskTypeTags: ['원가_상승_부담형', '단기_매출_정체형'],
    agency: '소상공인시장진흥공단', target: '업력 무관 소상공인', limit: '총 3조 3,620억원 규모 (개별 한도 확인 필요)', rate: NEED, period: '2026년', url: '',
    content: '임대료·인건비·재료비 등 운전자금이 필요할 때 가장 먼저 검토할 수 있는 자금. 소진공 직접대출 또는 금융기관 대리대출, 2026년부터 비대면 원스톱 신청 확대.',
    actionType: 'LINK_GUIDE', actionLabel: '지원 대상 자격 확인하기', updatedAt: '2026-08-19',
  },
  {
    docId: 'POL_005', title: '희망리턴패키지 (폐업 소상공인 재기지원)', riskTypeTags: ['상권_침체_붕괴형'],
    agency: '소상공인시장진흥공단', target: '폐업 (예정) 소상공인', limit: NEED, rate: NEED, period: NEED, url: '',
    content: '폐업 소상공인의 취업·재창업 프로그램 연계. 새출발기금 약정 체결 폐업자가 재기사업화 프로그램을 수료하면 공공정보 해제 1회 신청 가능.',
    actionType: 'LINK_GUIDE', actionLabel: '재기지원 프로그램 안내받기', updatedAt: '2026-08-19',
  },
  {
    docId: 'POL_006', title: '이차보전 사업 (금리 지원)', riskTypeTags: ['고금리_과다채무형', '원가_상승_부담형'],
    agency: '중소벤처기업부', target: '민간 금융기관 대출 보유 중소벤처기업', limit: '총 3,670억원 규모', rate: '대출이자 일부 보전', period: '2026년', url: '',
    content: '민간 금융기관 대출금 이자 일부를 지원. 시중은행 대출을 유지하면서 이자 부담만 낮출 수 있어 기존 대출 보유 소상공인에게 적합.',
    actionType: 'LINK_GUIDE', actionLabel: '이차보전 대상 확인하기', updatedAt: '2026-08-19',
  },
  {
    docId: 'POL_007', title: '경영안정 바우처 및 디지털 전환 지원', riskTypeTags: ['단기_매출_정체형', '원가_상승_부담형'],
    agency: '소상공인시장진흥공단 · 지역 소상공인센터', target: '경쟁 심화·운영비 부담 소상공인', limit: NEED, rate: '해당 없음 (바우처)', period: '2026년', url: '',
    content: 'POS·회계 프로그램·챗봇 등 디지털 전환 솔루션 도입 지원, 지역 소상공인센터 무료 컨설팅. 자금 외 운영 효율화 측면 제도.',
    actionType: 'LINK_GUIDE', actionLabel: '바우처 신청 방법 보기', updatedAt: '2026-08-19',
  },
  {
    docId: 'POL_008', title: '청년 소상공인 특화 자금', riskTypeTags: ['단기_매출_정체형'],
    agency: '소상공인시장진흥공단', target: '만 39세 이하 청년 소상공인 또는 청년 고용 매장', limit: NEED, rate: '정책자금 기준금리 (변동)', period: '거치 2년 포함 5년 이내', url: '',
    content: '업력이 짧아 자금 애로를 겪는 청년 창업 소상공인의 초기 정착 지원.',
    actionType: 'LINK_GUIDE', actionLabel: '청년 특화자금 안내받기', updatedAt: '2026-08-19',
  },
];

export const RISK_TYPE_QUERY: Record<RiskType, string | null> = {
  고금리_과다채무형: '대출 상환 부담이 크고 연체가 발생한 소상공인을 위한 채무조정 및 금리 지원 제도',
  매출_폭락형: '매출이 급격히 감소해 긴급 운전자금이 필요한 소상공인 지원 제도',
  상권_침체_붕괴형: '상권 침체로 폐업 위기에 놓인 소상공인의 재기 지원 제도',
  원가_상승_부담형: '원재료비·인건비 상승으로 경영이 어려운 소상공인 지원 제도',
  단기_매출_정체형: '동일업종 경쟁 심화, 임대료 부담으로 매출이 정체된 소상공인 지원 제도',
  정상_유지형: null,
};

/** 목업용 키워드 점수 (실서비스: 임베딩 코사인 + BM25 결합 — F-RAG-03) */
function keywordScore(query: string, doc: PolicyDoc) {
  const toks = query.split(/[\s,·]+/).filter((t) => t.length >= 2);
  const text = doc.title + ' ' + doc.content + ' ' + doc.target;
  return toks.reduce((s, t) => s + (text.includes(t.slice(0, 2)) ? 1 : 0), 0) / Math.max(1, toks.length);
}

/** F-RAG-03: risk_type 필터 → 점수 정렬 → top_k 미만이면 전체 코퍼스로 폴백 */
export function retrieve(riskType: RiskType, topK = 3, extraQuery = ''): { docs: PolicyDoc[]; fallback: boolean } {
  const q = (RISK_TYPE_QUERY[riskType] ?? '') + ' ' + extraQuery;
  if (!q.trim()) return { docs: [], fallback: false };
  const rank = (ds: PolicyDoc[]) => [...ds].sort((a, b) => keywordScore(q, b) - keywordScore(q, a));
  const tagged = rank(POLICY_DOCS.filter((d) => d.riskTypeTags.includes(riskType)));
  if (tagged.length >= topK) return { docs: tagged.slice(0, topK), fallback: false };
  const rest = rank(POLICY_DOCS.filter((d) => !tagged.includes(d)));
  return { docs: [...tagged, ...rest].slice(0, topK), fallback: true };
}

export function toSolution(d: PolicyDoc): Solution {
  return {
    solutionId: d.docId, title: d.title, agency: d.agency, summary: d.content.slice(0, 90) + (d.content.length > 90 ? '…' : ''),
    limit: d.limit, rate: d.rate, url: d.url, actionType: d.actionType, actionLabel: d.actionLabel,
  };
}
