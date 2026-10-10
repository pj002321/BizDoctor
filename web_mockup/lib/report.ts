/**
 * AI 리포트 목업 (F-LLM-01/02/05, F-SYS-07).
 * ⚠ LLM 호출 없이 템플릿으로 생성 — 스트리밍·가드레일·캐시 흐름만 재현.
 * 실서비스: signal JSON + 검색 문서만 컨텍스트로 LLM 호출, '제공된 문서 밖 정보 생성 금지' 프롬프트.
 */
import { DIAG_GRADE, RISK_TYPE_META } from './risk';
import { POLICY_DOCS } from './policies';
import { store } from './store';
import type { SignalResponse } from './types';

/** F-LLM-05 한계 고지 — 모든 리포트 하단 고정, 제거 불가 */
export const DISCLAIMER =
  '※ 매출 시계열은 시뮬레이션 기반이며, 정확도는 시뮬레이션 규칙 복원율입니다. ' +
  '지원사업의 자격·한도·금리·신청기간은 반드시 소관기관 공고에서 최종 확인하세요.';

/** 사업장 고유값이 없는 부분 — (등급, 유형, 업종, 자치구) 키로 캐싱 (F-SYS-07) */
function genericPart(d: SignalResponse) {
  const meta = RISK_TYPE_META[d.riskType];
  const lines = [
    `## 추정 원인`,
    `모델이 추정한 원인 유형은 **${meta.name}**입니다. 확정 진단이 아닌 추정이며, 아래 확률과 함께 해석해야 합니다.`,
    ``,
    `## 권장 조치`,
    ...(d.riskLevel === 'GREEN'
      ? ['- 현재 흐름을 유지하면서 분기마다 매출 지수를 다시 점검하세요.']
      : d.riskLevel === 'YELLOW'
      ? ['- 고정비(임대료·인건비) 항목을 점검하고 매출 정체 원인을 확인하세요.', '- 아래 지원사업 중 자격 요건이 맞는 제도를 먼저 확인하세요.']
      : ['- 단기 운전자금 확보 방안을 우선 검토하세요.', '- 대출이 있다면 상환 일정과 금리 조건을 정리해 상담기관에 문의하세요.', '- 아래 지원사업의 신청 요건을 바로 확인하세요.']),
    ``,
    `## 지원사업`,
    ...(d.solutions.length
      ? d.solutions.map((s) => `- **${s.title}** — ${s.agency}. 한도: ${s.limit}. 금리: ${s.rate}.`)
      : ['- 현재 진단 유형에 연결된 지원사업 문서가 없습니다.']),
  ];
  return lines.join('\n');
}

/** 사업장 고유값 — 캐시 제외, 매 요청 생성 */
function uniquePart(d: SignalResponse) {
  const g = DIAG_GRADE[d.riskLevel];
  const pct = (v: number) => (v * 100).toFixed(1);
  return [
    `# ${d.input.dong} ${d.input.serviceName} 진단 리포트`,
    ``,
    `## 현황 요약`,
    `- 진단 등급: **${g.grade} · ${g.label}** (보정 후 확률 ${pct(d.levelProbs[d.riskLevel])}%)`,
    `- 최근 3개월 매출 지수: ${d.revenueIndex.join(' → ')} (1개월차=100)`,
    `- 위험 점수: ${d.score} / 100`,
    `- 상권 내 위치: 같은 업종 중 폐업 위험 상위 ${d.context.topPercent}%`,
    `- 추정 원인 확률: ${pct(d.typeProbs[d.riskType])}%`,
  ].join('\n');
}

/** F-LLM-02 가드레일: 리포트 속 모든 수치·지원사업명이 입력 컨텍스트에 존재하는지 대조 */
export function verify(report: string, d: SignalResponse) {
  const allowed = new Set<string>();
  const addNum = (v: number) => { allowed.add(String(v)); allowed.add(v.toFixed(1)); };
  [...d.revenueIndex, d.score, d.context.topPercent, 100, 1, 3].forEach(addNum);
  Object.values(d.levelProbs).forEach((v) => addNum(+(v * 100).toFixed(1)));
  Object.values(d.typeProbs).forEach((v) => addNum(+(v * 100).toFixed(1)));
  const ctxText = d.solutions.map((s) => `${s.title} ${s.limit} ${s.rate} ${s.agency}`).join(' ');
  const body = report.replace(DISCLAIMER, '');
  const nums = body.match(/\d+(?:\.\d+)?/g) ?? [];
  const badNums = nums.filter((n) => !allowed.has(n) && !ctxText.includes(n) && !d.input.dong.includes(n));
  const titles = [...body.matchAll(/\*\*([^*]+)\*\*/g)].map((m) => m[1]);
  const knownTitles = new Set(POLICY_DOCS.map((p) => p.title));
  const badTitles = titles.filter((t) => knownTitles.has(t) === false && /자금|기금|사업|조정|패키지|바우처/.test(t) && !d.solutions.some((s) => s.title === t));
  return { ok: badNums.length === 0 && badTitles.length === 0, checkedNumbers: nums.length, badNums, badTitles };
}

export function buildReport(d: SignalResponse) {
  const key = [d.riskLevel, d.riskType, d.input.service, d.input.gu].join('|');
  let generic = store.reportCache.get(key);
  let cacheHit = true;
  if (!generic) {
    cacheHit = false;
    generic = genericPart(d);
    // 캐시 저장 전 사업장 고유값 혼입 검사 — 섞였으면 캐싱하지 않음
    const uniques = [d.input.dong, String(d.score), d.revenueIndex.join(' → ')];
    if (!uniques.some((u) => generic!.includes(u))) store.reportCache.set(key, generic);
  }
  store.metrics[cacheHit ? 'reportCacheHits' : 'reportCacheMiss']++;
  const report = `${uniquePart(d)}\n\n${generic}\n\n---\n${DISCLAIMER}`;
  const check = verify(report, d);
  if (!check.ok) store.metrics.guardrailFail++;
  // 검증 실패 시: 재생성 1회 → 재실패면 템플릿 폴백 (목업은 이미 템플릿이므로 그대로 반환)
  return { report, cacheHit, check };
}
