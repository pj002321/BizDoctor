/**
 * 사업장 진단 목업 로직 (F-DIA-01~08).
 * ⚠ 실제 모델(risk_model.keras) 추론이 아니라, 동일한 입·출력 형태를 흉내내는 규칙 기반 대체 로직.
 *   백엔드 연결 시 POST /api/diagnosis 가 실제 모델 결과를 돌려주면 화면은 그대로 동작함.
 */
import crypto from 'node:crypto';
import { cellSeries, dongByCode, getIndustryDist, serviceByCode } from './data';
import { retrieve, toSolution } from './policies';
import { BASE_RED_RATE, REAL_RED_RATE, RISK_TYPE_META, RISK_TYPES } from './risk';
import type { DiagnosisContext, DiagnosisRequest, RiskType, Signal, SignalResponse } from './types';

const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const sig = (x: number) => 1 / (1 + Math.exp(-x));
const r = (v: number, d = 3) => Math.round(v * 10 ** d) / 10 ** d;

/** F-DIA-04 사전확률 보정: p'(c) ∝ p(c) × (실제 사전확률 / 학습 사전확률) */
export function priorCorrect(p: Record<Signal, number>): Record<Signal, number> {
  const wRed = REAL_RED_RATE / BASE_RED_RATE;
  const wOther = (1 - REAL_RED_RATE) / (1 - BASE_RED_RATE);
  const raw = { GREEN: p.GREEN * wOther, YELLOW: p.YELLOW * wOther, RED: p.RED * wRed };
  const s = raw.GREEN + raw.YELLOW + raw.RED;
  return { GREEN: r(raw.GREEN / s), YELLOW: r(raw.YELLOW / s), RED: r(raw.RED / s) };
}

export class InputError extends Error {}

export function context(dongCode: string, service: string): DiagnosisContext & { asOf: string; closeRate: number; openRate: number; franchiseShare: number } {
  const series = cellSeries(dongCode, service);
  if (!series) throw new InputError('해당 행정동·업종 조합의 상권 데이터가 없습니다.');
  const last = [...series].reverse().find((p) => p.percentile != null)!;
  const svc = serviceByCode(service)!;
  const dist = getIndustryDist()[service] ?? { n: 0, hist: Array(20).fill(0) };
  const pct = last.percentile ?? 0.5;
  const top = Math.max(1, Math.round((1 - pct) * 100));
  const d = dongByCode(dongCode)!;
  return {
    percentile: r(pct), topPercent: top, hist: dist.hist, peers: dist.n,
    sentence: `서울 ${svc.name} ${dist.n.toLocaleString()}개 행정동 중 폐업 위험 상위 ${top}% (${d.name}, ${last.quarter})`,
    asOf: last.quarter, closeRate: last.closeRate ?? 0, openRate: last.openRate ?? 0,
    franchiseShare: r(last.franchiseShare ?? 0),
  };
}

export function diagnose(req: DiagnosisRequest): SignalResponse {
  // ---- F-DIA-01 입력 검증 + 지수 정규화 (금액은 여기서만 사용, 저장 안 함) ----
  const d = dongByCode(req.dongCode);
  const svc = serviceByCode(req.service);
  if (!d) throw new InputError('행정동을 선택해 주세요.');
  if (!svc) throw new InputError('업종을 선택해 주세요.');
  if (!Array.isArray(req.revenue) || req.revenue.length !== 3 || req.revenue.some((v) => !(v > 0)))
    throw new InputError('최근 3개월 매출을 모두 0보다 큰 금액으로 입력해 주세요.');
  const base = req.revenue[0];
  const idx = req.revenue.map((v) => r((v / base) * 100, 1)) as [number, number, number];

  // ---- F-DIA-02 정적 피처 조인 (최신 분기) ----
  const series = cellSeries(req.dongCode, req.service)!;
  const ctx = context(req.dongCode, req.service);
  const lastRow = [...series].reverse().find((p) => p.percentile != null)!;
  const kosis = svc.kosis || '전산업';

  // ---- F-DIA-03 (대체 로직) 등급 원확률: 학습분포(RED 30%) 기준이라고 가정 ----
  const slope = (idx[2] - idx[0]) / 2; // 월평균 지수 변화
  const riskRaw = 0.55 * ctx.percentile + 0.45 * clamp(-slope / 15, 0, 1);
  const pRed = sig((riskRaw - 0.5) * 9);
  const pYellow = (1 - pRed) * sig((riskRaw - 0.3) * 9);
  const rawProbs = { RED: pRed, YELLOW: pYellow, GREEN: 1 - pRed - pYellow };
  const levelProbs = priorCorrect(rawProbs); // F-DIA-04 — 보정 전 확률은 응답에 포함하지 않음
  const riskLevel = (Object.entries(levelProbs).sort((a, b) => b[1] - a[1])[0][0]) as Signal;

  // ---- F-DIA-05 원인 유형 (등급 확률 × 유형 내 비중) ----
  const share: Record<RiskType, number> = {
    정상_유지형: 1,
    단기_매출_정체형: slope < 0 ? 0.65 : 0.4,
    원가_상승_부담형: slope < 0 ? 0.35 : 0.6,
    매출_폭락형: slope < -10 ? 0.55 : 0.2,
    상권_침체_붕괴형: (lastRow.closeOpenGap ?? 0) > 0 ? 0.35 : 0.15,
    고금리_과다채무형: 0,
  };
  share.고금리_과다채무형 = 1 - share.매출_폭락형 - share.상권_침체_붕괴형;
  const typeProbs = Object.fromEntries(
    RISK_TYPES.map((t) => [t, r(levelProbs[RISK_TYPE_META[t].level] * share[t])]),
  ) as Record<RiskType, number>;
  const riskType = RISK_TYPES.filter((t) => RISK_TYPE_META[t].level === riskLevel).sort((a, b) => typeProbs[b] - typeProbs[a])[0];

  // ---- F-DIA-06 위험 점수 ----
  let score: number; let scoreMethod: SignalResponse['scoreMethod'];
  if (req.prevRevenue && req.prevRevenue.every((v) => v > 0)) {
    const prev = req.prevRevenue.reduce((a, b) => a + b, 0);
    const cur = req.revenue.reduce((a, b) => a + b, 0);
    score = clamp(((prev - cur) / prev) * 100, 0, 100); scoreMethod = 'six_month_drop';
  } else {
    score = clamp(-slope * 3, 0, 100); scoreMethod = 'three_month_slope';
  }

  // ---- F-RAG-03/04 지원사업 ----
  const { docs } = retrieve(riskType, 3);
  const meta = RISK_TYPE_META[riskType];
  const theme = riskLevel === 'RED' ? 'pulse_warning' : riskLevel === 'YELLOW' ? 'blink_caution' : 'soft_glow';

  const now = new Date();
  const res: SignalResponse = {
    diagnosisId: 'DX-' + crypto.randomBytes(4).toString('hex').toUpperCase(),
    shareToken: crypto.randomBytes(9).toString('base64url'),
    createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + 24 * 3600 * 1000).toISOString(),
    input: { dongCode: d.code, dong: d.name, gu: d.gu, service: svc.code, serviceName: svc.name, industry: kosis },
    revenueIndex: idx,
    riskLevel, levelProbs, priorCorrected: true,
    riskType, typeProbs,
    lowConfidence: riskLevel === 'YELLOW' || meta.recall === 0 || (meta.recall ?? 1) < 0.05 || typeProbs[riskType] < 0.5,
    score: Math.round(score * 10) / 10, scoreMethod,
    context: { percentile: ctx.percentile, topPercent: ctx.topPercent, hist: ctx.hist, peers: ctx.peers, sentence: ctx.sentence },
    visualTheme: { bgColor: meta.color, animation: theme, impactMessage: meta.message },
    solutions: docs.map(toSolution),
    features: { percentile: ctx.percentile, closeRate: ctx.closeRate, openRate: ctx.openRate, franchiseShare: ctx.franchiseShare, kosisIndustry: kosis, fallback: !svc.kosis, asOf: ctx.asOf },
  };
  return res;
}
