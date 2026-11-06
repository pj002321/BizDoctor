import { describe, expect, it } from "vitest";
import { SAMPLE_SIGNAL } from "../sample";
import { buildReport, checkNumbers } from "./buildReport";

describe("buildReport", () => {
  it("모든 숫자가 진단 결과에 있다 (가드레일 통과)", () => {
    const text = buildReport(SAMPLE_SIGNAL)
      .map((x) => x.body)
      .join("\n");
    expect(checkNumbers(text, SAMPLE_SIGNAL)).toEqual([]);
  });
  it("근거에 없는 숫자는 잡아낸다", () => {
    expect(
      checkNumbers("한도는 7억 3천만원, 금리 2.9%", SAMPLE_SIGNAL),
    ).toEqual(expect.arrayContaining(["2.9"]));
  });
  it("정상 유지형이면 지원사업 단락을 쓰지 않는다", () => {
    const s = {
      ...SAMPLE_SIGNAL,
      risk_type: "정상_유지형" as const,
      solutions: [],
    };
    expect(buildReport(s).map((x) => x.heading)).not.toContain(
      "먼저 확인해 볼 지원사업",
    );
  });
});
