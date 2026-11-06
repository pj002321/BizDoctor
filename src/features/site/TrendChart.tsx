"use client";
import { useEffect, useRef, useState } from "react";
import CountUp from "@/components/CountUp";
import data from "./data/seoul.json";

const W = 560;
const H = 240;
const pad = { l: 36, r: 16, t: 16, b: 30 };
const COLORS = ["var(--color-lamp-red)", "var(--color-fg)"];
const N = data.quarters.length;

const all = data.trend.flatMap((t) => t.values.filter((v) => v != null));
const lo = Math.floor(Math.min(...all)) - 0.5;
const hi = Math.ceil(Math.max(...all)) + 0.5;
const x = (i: number) => pad.l + (i * (W - pad.l - pad.r)) / (N - 1);
const y = (v: number) => pad.t + ((hi - v) * (H - pad.t - pad.b)) / (hi - lo);
const ticks = [lo + 0.5, (lo + hi) / 2, hi - 0.5].map((v) => Math.round(v));
const pts = (vals: (number | null)[]) =>
  vals.map((v, i) => (v == null ? "" : `${x(i)},${y(v)}`)).join(" ");

/**
 * 분기별 평균 폐업률 추이. 화면에 들어오면 선이 그려지고,
 * 마우스·손가락·좌우 화살표로 분기를 고르면 위쪽 수치가 그 분기 값으로 바뀐다.
 */
export default function TrendChart() {
  const ref = useRef<HTMLDivElement>(null);
  const [on, setOn] = useState(N - 1);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        el.classList.add("is-in");
        io.disconnect();
      },
      { rootMargin: "0px 0px -15% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const pick = (e: React.PointerEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const i = Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (N - 1));
    setOn(Math.max(0, Math.min(N - 1, i)));
  };

  return (
    <div
      ref={ref}
      data-ui
      className="trend rounded-[var(--radius-card)] bg-bg p-6 sm:p-8"
    >
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div>
          <p className="text-sm text-muted">분기별 평균 폐업률</p>
          <p className="mt-1 text-xl font-bold" aria-live="polite">
            {data.quarters[on]}
          </p>
        </div>
        <dl className="flex gap-8">
          {data.trend.map((t, k) => (
            <div key={t.label}>
              <dt className="flex items-center gap-1.5 text-sm text-muted">
                <span
                  className="inline-block h-[3px] w-4"
                  style={{ background: COLORS[k] }}
                />
                {t.label}
              </dt>
              <dd className="text-[2rem] leading-tight font-bold tracking-[-0.03em]">
                <CountUp to={t.values[on] ?? 0} decimals={2} duration={600} />
                <span className="text-lg">%</span>
              </dd>
            </div>
          ))}
        </dl>
      </div>
      <div
        className="mt-6 w-full cursor-crosshair touch-pan-y outline-none focus-visible:outline-3 focus-visible:outline-offset-4 focus-visible:outline-accent"
        role="slider"
        tabIndex={0}
        aria-label="분기 고르기"
        aria-valuemin={0}
        aria-valuemax={N - 1}
        aria-valuenow={on}
        aria-valuetext={`${data.quarters[on]}: ${data.trend
          .map((t) => `${t.label} ${t.values[on]}%`)
          .join(", ")}`}
        onPointerMove={pick}
        onPointerDown={pick}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") setOn((v) => Math.max(0, v - 1));
          else if (e.key === "ArrowRight") setOn((v) => Math.min(N - 1, v + 1));
          else return;
          e.preventDefault();
        }}
      >
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="block w-full"
          aria-hidden="true"
        >
          {ticks.map((v) => (
            <g key={v}>
              <line
                x1={pad.l}
                x2={W - pad.r}
                y1={y(v)}
                y2={y(v)}
                stroke="var(--color-surface)"
              />
              <text
                x={pad.l - 8}
                y={y(v) + 4}
                textAnchor="end"
                fontSize="13"
                fill="var(--color-muted)"
              >
                {v}
              </text>
            </g>
          ))}
          {data.quarters.map((q, i) =>
            i % 2 === 0 ? (
              <text
                key={q}
                x={x(i)}
                y={H - 6}
                textAnchor="middle"
                fontSize="13"
                fill={i === on ? "var(--color-fg)" : "var(--color-muted)"}
              >
                {q.replace("20", "").replace(" ", "")}
              </text>
            ) : null,
          )}

          {/* 음식점 선 아래 면: 선보다 늦게 차오른다 */}
          <polygon
            className="trend-area"
            fill="var(--color-lamp-red)"
            points={`${x(0)},${H - pad.b} ${pts(data.trend[0].values)} ${x(N - 1)},${H - pad.b}`}
          />

          <line
            className="transition-transform duration-500 ease-[var(--ease-out-expo)]"
            style={{ transform: `translateX(${x(on)}px)` }}
            x1={0}
            x2={0}
            y1={pad.t}
            y2={H - pad.b}
            stroke="var(--color-fg)"
            strokeWidth="1.5"
            strokeDasharray="3 4"
          />

          {data.trend.map((t, k) => (
            <g key={t.label}>
              <polyline
                className="trend-line"
                style={{ ["--k" as string]: k }}
                pathLength={1}
                fill="none"
                stroke={COLORS[k]}
                strokeWidth="2.75"
                strokeLinejoin="round"
                strokeLinecap="round"
                points={pts(t.values)}
              />
              {t.values.map((v, i) =>
                v == null ? null : (
                  <circle
                    key={data.quarters[i]}
                    className="trend-dot"
                    style={{ ["--d" as string]: i + k * 2 }}
                    cx={x(i)}
                    cy={y(v)}
                    r={i === on ? 6 : 3.5}
                    fill={i === on ? "white" : COLORS[k]}
                    stroke={COLORS[k]}
                    strokeWidth={i === on ? 3 : 0}
                  />
                ),
              )}
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}
