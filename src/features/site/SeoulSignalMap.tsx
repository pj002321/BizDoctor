"use client";
import Link from "next/link";
import { useState } from "react";
import CountUp from "@/components/CountUp";
import { Arrow, MARKET_SIGNAL, SignalShape } from "@/components/icons";
import data from "./data/seoul.json";

type Counts = {
  g: number;
  y: number;
  r: number;
  low: number;
  watch: [string, number, string | null][];
};
const stats = data.stats as unknown as Record<string, Record<string, Counts>>;
const FILTERS = [
  ["all", "전체 업종"],
  ...data.industries.map((l, i) => [String(i), l]),
] as const;

/** 판정된 칸 가운데 '주의' 이상 비율. 지도 농도로만 쓴다. */
const share = (c?: Counts) =>
  c && c.g + c.y + c.r ? (c.y + c.r) / (c.g + c.y + c.r) : 0;

export default function SeoulSignalMap() {
  const [ind, setInd] = useState("all");
  const [gu, setGu] = useState("마포구");
  const max = Math.max(
    ...data.map.shapes.map((s) => share(stats[s.gu][ind])),
    0.01,
  );
  const c = stats[gu][ind];
  const judged = c ? c.g + c.y + c.r : 0;

  return (
    <div className="grid gap-8 lg:grid-cols-[1.35fr_1fr] lg:gap-20">
      <div>
        <fieldset>
          <legend className="sr-only">업종 고르기</legend>
          <div className="flex flex-wrap gap-2">
            {FILTERS.map(([k, label]) => (
              <label key={k} className="cursor-pointer">
                <input
                  type="radio"
                  name="industry"
                  value={k}
                  checked={ind === k}
                  onChange={() => setInd(k)}
                  className="peer sr-only"
                />
                <span className="inline-block rounded-full bg-surface px-4 py-2 text-[0.9375rem] font-medium transition-colors duration-150 peer-checked:bg-night peer-checked:text-white peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent hover:bg-[#e2e5e2] peer-checked:hover:bg-night">
                  {label}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <p className="mt-4 text-sm text-muted">
          초록에 가까울수록 ‘양호’ 칸이, 노랑에 가까울수록 ‘주의’ 칸 비율이
          높습니다.
        </p>

        {/* biome-ignore lint/a11y/useSemanticElements: SVG 안에는 fieldset 을 쓸 수 없다 */}
        <svg
          data-ui
          viewBox={`0 0 ${data.map.width} ${data.map.height}`}
          className="mt-4 w-full"
          role="group"
          aria-label="서울 25개 자치구 지도. 자치구를 누르면 오른쪽에 결과가 나옵니다."
        >
          {data.map.shapes.map((s) => {
            const t = share(stats[s.gu][ind]) / max;
            const on = s.gu === gu;
            return (
              // biome-ignore lint/a11y/useSemanticElements: SVG 지도 조각은 button 요소로 만들 수 없다
              <g
                key={s.gu}
                role="button"
                tabIndex={0}
                aria-pressed={on}
                aria-label={`${s.gu} 보기`}
                className="cursor-pointer outline-none [&:focus-visible>path]:stroke-fg [&:focus-visible>path]:stroke-[3]"
                onClick={() => setGu(s.gu)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setGu(s.gu);
                  }
                }}
              >
                <path
                  d={s.d}
                  fill={
                    on
                      ? "var(--color-night)"
                      : `color-mix(in oklab, color-mix(in oklab, var(--color-lamp-yellow) ${Math.round(t * 100)}%, var(--color-lamp-green)) ${38 + t * 40}%, white)`
                  }
                  stroke="white"
                  strokeWidth="1.5"
                  className="transition-[fill] duration-500 ease-[var(--ease-out-expo)] hover:brightness-95"
                />
                <text
                  x={s.cx}
                  y={s.cy}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="12.5"
                  fontWeight={on ? 700 : 500}
                  fill={on ? "white" : "var(--color-fg)"}
                  className="pointer-events-none select-none transition-[fill] duration-300"
                >
                  {s.gu.replace("구", "")}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div
        className="self-start rounded-[var(--radius-card)] bg-surface p-6 sm:p-10"
        aria-live="polite"
      >
        <h3
          key={gu + ind}
          className="fade-up text-3xl font-bold tracking-[-0.03em]"
          style={{ ["--i" as string]: -4 }}
        >
          {gu}
        </h3>
        <p className="mt-1 text-muted">
          {FILTERS.find(([k]) => k === ind)?.[1]} · 행정동 × 산업{" "}
          {judged + (c?.low ?? 0)}칸
        </p>

        <ul data-ui className="mt-8 grid grid-cols-2 gap-3">
          {(["g", "y", "r"] as const).map((s) => (
            <li key={s} className="rounded-xl bg-bg p-5">
              <span className="flex items-center gap-2 text-sm font-semibold">
                <SignalShape s={s} /> {MARKET_SIGNAL[s].label}
              </span>
              <span className="mt-1 block text-3xl font-bold">
                <CountUp to={c?.[s] ?? 0} duration={700} />
              </span>
            </li>
          ))}
          <li className="rounded-xl bg-bg p-5">
            <span className="text-sm font-semibold text-muted">표본 적음</span>
            <span className="mt-1 block text-3xl font-bold text-muted">
              <CountUp to={c?.low ?? 0} duration={700} />
            </span>
          </li>
        </ul>

        <div className="mt-6">
          <p className="text-sm font-semibold">눈여겨볼 행정동</p>
          {c?.watch.length ? (
            <ul className="mt-2 grid gap-1.5">
              {c.watch.map(([dong, w, industry]) => (
                <li
                  key={dong + w + industry}
                  className="flex items-center justify-between gap-3 text-[0.9375rem]"
                >
                  <span className="flex items-center gap-2">
                    <SignalShape s={w > 0.85 ? "r" : "y"} size={10} />
                    {dong}
                    {industry && (
                      <span className="text-sm text-muted">
                        {industry.split(/[ ,]/)[0]}
                      </span>
                    )}
                  </span>
                  <span className="text-sm text-muted">
                    위험가중치 {w.toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-[0.9375rem] text-muted">
              이 조건에서는 ‘주의’ 이상인 행정동이 없습니다.
            </p>
          )}
        </div>

        <Link
          href={`/market?gu=${encodeURIComponent(gu)}`}
          className="btn btn-quiet mt-8 w-full justify-between"
        >
          {gu} 행정동 성적표 보기 <Arrow />
        </Link>
      </div>
    </div>
  );
}
