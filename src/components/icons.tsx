/** 사이트 공통 아이콘. 선 굵기 2, 각진 끝 하나로 통일한다. */

export function Arrow({ className }: { className?: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      aria-hidden="true"
      className={className}
    >
      <path
        d="M2 8h11M9 4l4 4-4 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="square"
      />
    </svg>
  );
}

export function Check() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      aria-hidden="true"
      className="shrink-0"
    >
      <rect width="18" height="18" rx="9" fill="var(--color-accent)" />
      <path
        d="M5 9.2l2.6 2.6L13 6.4"
        fill="none"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="square"
      />
    </svg>
  );
}

/** 상권 신호등 모양: 양호 ● · 주의 ▲ · 위험 ■ (F-SYS-04 색 단독 전달 금지) */
export type MarketSignal = "g" | "y" | "r";
export const MARKET_SIGNAL: Record<
  MarketSignal,
  { label: string; color: string; rule: string }
> = {
  g: { label: "양호", color: "var(--color-signal-green)", rule: "0.60 이하" },
  y: {
    label: "주의",
    color: "var(--color-signal-yellow)",
    rule: "0.60 초과 ~ 0.85",
  },
  r: { label: "위험", color: "var(--color-signal-red)", rule: "0.85 초과" },
};

export function SignalShape({
  s,
  size = 12,
}: {
  s: MarketSignal;
  size?: number;
}) {
  const c = MARKET_SIGNAL[s].color;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 12 12"
      aria-hidden="true"
      className="shrink-0"
    >
      {s === "g" && <circle cx="6" cy="6" r="6" fill={c} />}
      {s === "y" && <path d="M6 0.5L11.8 11.5H0.2Z" fill={c} />}
      {s === "r" && <rect width="12" height="12" fill={c} />}
    </svg>
  );
}
