/**
 * 사업장 진단 순수 함수. DB·모델 없이 테스트한다.
 *
 * ⚠ estimateRawProbs · causeShares 는 실제 모델(risk_model.keras) 대신 쓰는 **목업 규칙**이다.
 *   ai-service 가 연결되면 이 둘은 지우고, toSalesIndex · priorCorrect 만 남긴다.
 */
import {
  RISK_TYPE_LEVEL,
  type RiskLevel,
  type RiskType,
} from "@/shared/types/signal";

/** 학습 위험군 비중(의도적 과표집)과 서울 실제 비중. F-DIA-04 */
export const PRIOR_TRAIN_RED = 0.3;
export const PRIOR_REAL_RED = 0.14;

const round = (v: number, d = 3) => Math.round(v * 10 ** d) / 10 ** d;
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const sigmoid = (x: number) => 1 / (1 + Math.exp(-x));

/** 매출 3개월을 1개월차 = 100 지수로 바꾼다. 실금액은 여기서만 쓰고 버린다(F-SYS-05). */
export function toSalesIndex(sales: number[]): [number, number, number] {
  if (sales.length !== 3 || sales.some((v) => !(Number.isFinite(v) && v > 0)))
    throw new RangeError("최근 3개월 매출을 모두 0보다 큰 숫자로 넣어 주세요.");
  return sales.map((v) => round((v / sales[0]) * 100, 1)) as [
    number,
    number,
    number,
  ];
}

/** 사전확률 보정: p'(c) ∝ p(c) × 실제 사전확률 / 학습 사전확률. 빼먹으면 모두의 위험도가 부푼다. */
export function priorCorrect(
  p: Record<RiskLevel, number>,
): Record<RiskLevel, number> {
  const wRed = PRIOR_REAL_RED / PRIOR_TRAIN_RED;
  const wOther = (1 - PRIOR_REAL_RED) / (1 - PRIOR_TRAIN_RED);
  const raw = {
    GREEN: p.GREEN * wOther,
    YELLOW: p.YELLOW * wOther,
    RED: p.RED * wRed,
  };
  const s = raw.GREEN + raw.YELLOW + raw.RED;
  return {
    GREEN: round(raw.GREEN / s),
    YELLOW: round(raw.YELLOW / s),
    RED: round(raw.RED / s),
  };
}

/** 목업 규칙: 업종 내 폐업률 위치와 3개월 기울기로 학습 분포 기준 원확률을 흉내 낸다. */
export function estimateRawProbs(
  index: [number, number, number],
  percentile: number,
): Record<RiskLevel, number> {
  const slope = (index[2] - index[0]) / 2;
  const risk = 0.55 * percentile + 0.45 * clamp(-slope / 15, 0, 1);
  const red = sigmoid((risk - 0.5) * 9);
  const yellow = (1 - red) * sigmoid((risk - 0.3) * 9);
  return { RED: red, YELLOW: yellow, GREEN: 1 - red - yellow };
}

export function pickLevel(p: Record<RiskLevel, number>): RiskLevel {
  return (Object.entries(p) as [RiskLevel, number][]).sort(
    (a, b) => b[1] - a[1],
  )[0][0];
}

/** 목업 규칙: 등급 확률을 같은 등급의 원인 유형들에 나눠 준다. */
export function causeProbs(
  levels: Record<RiskLevel, number>,
  index: [number, number, number],
  closeOpenGap: number,
): Record<RiskType, number> {
  const slope = (index[2] - index[0]) / 2;
  const crash = slope < -10 ? 0.55 : 0.2;
  const decline = closeOpenGap > 0 ? 0.35 : 0.15;
  const share: Record<RiskType, number> = {
    정상_유지형: 1,
    단기_매출_정체형: slope < 0 ? 0.65 : 0.4,
    원가_상승_부담형: slope < 0 ? 0.35 : 0.6,
    매출_폭락형: crash,
    상권_침체_붕괴형: decline,
    고금리_과다채무형: 1 - crash - decline,
  };
  return Object.fromEntries(
    (Object.keys(share) as RiskType[]).map((t) => [
      t,
      round(levels[RISK_TYPE_LEVEL[t]] * share[t]),
    ]),
  ) as Record<RiskType, number>;
}

/** 이 등급 안에서 확률이 가장 높은 유형과, 등급 안에서의 상대 확신도 */
export function pickCause(
  level: RiskLevel,
  probs: Record<RiskType, number>,
): { type: RiskType; confidence: number } {
  const same = (Object.keys(probs) as RiskType[]).filter(
    (t) => RISK_TYPE_LEVEL[t] === level,
  );
  const total = same.reduce((s, t) => s + probs[t], 0) || 1;
  const type = same.sort((a, b) => probs[b] - probs[a])[0];
  return { type, confidence: round(probs[type] / total, 2) };
}

/** 0~100 위험 점수: 3개월 하락 폭과 보정 위험확률을 섞는다. */
export function riskScore(
  index: [number, number, number],
  levels: Record<RiskLevel, number>,
): number {
  const drop = clamp(100 - index[2], 0, 100);
  return Math.round(
    clamp(0.5 * drop + 50 * (levels.RED + 0.5 * levels.YELLOW), 0, 100),
  );
}
