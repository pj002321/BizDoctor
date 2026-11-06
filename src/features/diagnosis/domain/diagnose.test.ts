import { describe, expect, it } from "vitest";
import {
  causeProbs,
  PRIOR_REAL_RED,
  PRIOR_TRAIN_RED,
  pickCause,
  priorCorrect,
  toSalesIndex,
} from "./diagnose";

describe("toSalesIndex", () => {
  it("1개월차를 100으로 놓는다", () => {
    expect(toSalesIndex([2_000_000, 1_880_000, 1_620_000])).toEqual([
      100, 94, 81,
    ]);
  });
  it("0 이하나 빈 값은 거절한다", () => {
    expect(() => toSalesIndex([100, 0, 50])).toThrow(RangeError);
    expect(() => toSalesIndex([100, Number.NaN, 50])).toThrow(RangeError);
    expect(() => toSalesIndex([100, 90])).toThrow(RangeError);
  });
});

describe("priorCorrect", () => {
  it("학습 분포 그대로면 실제 사전확률로 되돌린다", () => {
    const p = priorCorrect({ RED: PRIOR_TRAIN_RED, YELLOW: 0.35, GREEN: 0.35 });
    expect(p.RED).toBeCloseTo(PRIOR_REAL_RED, 3);
  });
  it("위험 확률을 낮추고 합은 1이다", () => {
    const p = priorCorrect({ RED: 0.6, YELLOW: 0.25, GREEN: 0.15 });
    expect(p.RED).toBeLessThan(0.6);
    expect(p.RED + p.YELLOW + p.GREEN).toBeCloseTo(1, 2);
  });
});

describe("pickCause", () => {
  it("같은 등급 안의 유형만 고른다", () => {
    const levels = { GREEN: 0.2, YELLOW: 0.3, RED: 0.5 };
    const probs = causeProbs(levels, [100, 80, 60], 1);
    const { type, confidence } = pickCause("RED", probs);
    expect(["매출_폭락형", "고금리_과다채무형", "상권_침체_붕괴형"]).toContain(
      type,
    );
    expect(confidence).toBeGreaterThan(0);
    expect(confidence).toBeLessThanOrEqual(1);
  });
});
