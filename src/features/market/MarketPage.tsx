// F-MAP: 지역(행정동 × 업종) 단위 "신호등". 사업장 결과(/diagnosis)와 섞지 않는다(F-SYS-01).
import Link from "next/link";
import CountUp from "@/components/CountUp";
import InView from "@/components/InView";
import { Arrow, MARKET_SIGNAL, SignalShape } from "@/components/icons";
import {
  GU_LIST,
  type GuData,
  loadGu,
  META,
  type Row,
  type Sig,
} from "./data/load";

type Q = { gu?: string; dong?: string; ind?: string; svc?: string };
const href = (q: Q) => {
  const p = new URLSearchParams(
    Object.entries(q).filter(([, v]) => v != null && v !== "") as [
      string,
      string,
    ][],
  );
  const s = p.toString();
  return `/market${s ? `?${s}` : ""}#explore`;
};
const LOW_STORES = 5; // 점포 5개 이하 = 표본 적음 (AGENTS.md)
const signalOf = (w: number): Sig => (w > 0.85 ? "r" : w > 0.6 ? "y" : "g");

export default function MarketPage({ q }: { q: Q }) {
  const ind = Math.max(
    0,
    Math.min(META.industries.length - 1, Number(q.ind ?? 0) || 0),
  );
  const gu = q.gu && GU_LIST.includes(q.gu) ? q.gu : undefined;
  const data = gu ? loadGu(gu) : null;
  const dong = data?.dongs.find((d) => d.code === q.dong);

  return (
    <main>
      <section className="bg-surface">
        <div className="frame grid gap-10 pt-14 pb-10 lg:grid-cols-[1fr_1fr] lg:items-end lg:gap-24 lg:pt-20">
          <h1 className="title">
            <span className="rise-line">
              <span>상권 신호등</span>
            </span>
          </h1>
          <p className="lead fade-up">
            서울 25개 자치구 · 425개 행정동의 업종별 폐업 통계(2023 Q1 – 2025
            Q3)를 지도에서 골라 행정동 성적표, 업종 상세 추이까지 좁혀 봅니다.
          </p>
        </div>
        <div className="frame pb-8">
          <Legend />
        </div>
      </section>

      <section
        id="explore"
        aria-labelledby="explore-h"
        className="frame scroll-mt-24 py-12 lg:py-16"
      >
        <h2 id="explore-h" className="sr-only">
          지역 고르기
        </h2>
        <nav
          aria-label="위치"
          className="flex flex-wrap items-center gap-2 text-[0.9375rem]"
        >
          <Link className="link-under" href={href({ ind: String(ind) })}>
            서울
          </Link>
          {gu && (
            <>
              <span aria-hidden="true">/</span>
              <Link
                className="link-under"
                href={href({ gu, ind: String(ind) })}
              >
                {gu}
              </Link>
            </>
          )}
          {dong && (
            <>
              <span aria-hidden="true">/</span>
              <span className="font-semibold">{dong.name}</span>
            </>
          )}
        </nav>

        <ul className="mt-6 flex flex-wrap gap-2" aria-label="산업 고르기">
          {META.industries.map((it, k) => (
            <li key={it.name}>
              <Link
                href={href({ gu, dong: dong?.code, ind: String(k) })}
                aria-current={k === ind ? "true" : undefined}
                className="inline-block rounded-full bg-surface px-4 py-2 text-[0.9375rem] font-medium transition-colors hover:bg-[#e2e5e2] aria-[current=true]:bg-night aria-[current=true]:text-white"
              >
                {it.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="mt-10">
          {!data ? (
            <SeoulLevel ind={ind} />
          ) : !dong ? (
            <GuLevel data={data} ind={ind} />
          ) : (
            <DongLevel data={data} dong={dong} ind={ind} svc={q.svc} />
          )}
        </div>
      </section>
    </main>
  );
}

function Legend() {
  return (
    <ul className="flex flex-wrap gap-x-8 gap-y-3 text-[0.9375rem]">
      {(["g", "y", "r"] as const).map((s) => (
        <li key={s} className="flex items-center gap-2">
          <SignalShape s={s} size={13} />
          <strong>{MARKET_SIGNAL[s].label}</strong>
          <span className="text-muted">위험가중치 {MARKET_SIGNAL[s].rule}</span>
        </li>
      ))}
      <li className="flex items-center gap-2">
        <LowBadge />
        <span className="text-muted">
          관측 8분기·점포 100 미만 칸, 점포 5개 이하 분기
        </span>
      </li>
    </ul>
  );
}

function LowBadge() {
  return (
    <span className="rounded-full bg-[#e2e5e2] px-2.5 py-0.5 text-[0.8125rem] font-semibold text-muted">
      표본 적음
    </span>
  );
}

/* ── 1단계: 서울 지도 ───────────────────────────── */
function SeoulLevel({ ind }: { ind: number }) {
  const sum = META.summary as Record<
    string,
    { g: number; y: number; r: number; low: number }[]
  >;
  const share = (g: string) => {
    const c = sum[g][ind];
    const n = c.g + c.y + c.r;
    return n ? (c.y + c.r) / n : 0;
  };
  const max = Math.max(...GU_LIST.map(share), 0.01);
  const ranked = [...GU_LIST].sort((a, b) => share(b) - share(a));

  return (
    <div className="grid gap-12 lg:grid-cols-[1.4fr_1fr] lg:gap-20">
      <div>
        <svg
          viewBox={`0 0 ${META.map.width} ${META.map.height}`}
          className="w-full"
          aria-label="서울 자치구 지도"
        >
          {META.map.shapes.map((s) => {
            const t = share(s.gu) / max;
            return (
              <Link
                key={s.gu}
                href={href({ gu: s.gu, ind: String(ind) })}
                aria-label={`${s.gu} 행정동 성적표 보기`}
                className="group outline-none"
              >
                <path
                  d={s.d}
                  fill={`color-mix(in oklab, color-mix(in oklab, var(--color-lamp-yellow) ${Math.round(t * 100)}%, var(--color-lamp-green)) ${38 + t * 40}%, white)`}
                  stroke="white"
                  strokeWidth="1.5"
                  className="transition-[filter] duration-200 group-hover:brightness-90 group-focus-visible:brightness-75"
                />
                <text
                  x={s.cx}
                  y={s.cy}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="12.5"
                  fontWeight="600"
                  fill="var(--color-fg)"
                  className="pointer-events-none"
                >
                  {s.gu.replace("구", "")}
                </text>
              </Link>
            );
          })}
        </svg>
        <p className="mt-3 text-sm text-muted">
          자치구를 누르면 행정동 성적표로 들어갑니다. 노랑에 가까울수록 ‘주의’
          칸 비율이 높습니다.
        </p>
      </div>

      <InView>
        <h3 className="text-xl font-bold">‘주의’ 이상 비율이 높은 자치구</h3>
        <ol className="mt-6 grid gap-1">
          {ranked.slice(0, 10).map((g, k) => {
            const c = sum[g][ind];
            return (
              <li key={g}>
                <Link
                  href={href({ gu: g, ind: String(ind) })}
                  className="grid grid-cols-[5rem_1fr_6.5rem] items-center gap-4 rounded-xl px-3 py-2.5 transition-colors hover:bg-surface"
                >
                  <span className="font-semibold">{g}</span>
                  <span className="h-2.5 rounded-full bg-surface">
                    <span
                      className="bar block h-full rounded-full bg-lamp-yellow"
                      style={{
                        width: `${(share(g) / max) * 100}%`,
                        ["--b" as string]: k,
                      }}
                    />
                  </span>
                  <span className="text-right text-[0.9375rem] text-muted">
                    주의 {c.y} · 위험 {c.r}
                  </span>
                </Link>
              </li>
            );
          })}
        </ol>
      </InView>
    </div>
  );
}

/* ── 2단계: 자치구 → 행정동 성적표 ─────────────────── */
function GuLevel({ data, ind }: { data: GuData; ind: number }) {
  const rows = data.dongs
    .map((d) => ({ d, c: d.ind[ind] }))
    .filter((x) => x.c)
    .sort((a, b) => {
      const w = (c: typeof a.c) => (c && c[0] !== "low" ? c[1] : -1);
      return w(b.c) - w(a.c);
    });
  const counts = { g: 0, y: 0, r: 0, low: 0 };
  for (const { c } of rows) if (c) counts[c[0] === "low" ? "low" : c[0]]++;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <h3 className="title">{data.gu} 행정동 성적표</h3>
        <ul className="flex gap-6 text-lg">
          {(["g", "y", "r"] as const).map((s) => (
            <li key={s} className="flex items-center gap-2">
              <SignalShape s={s} size={12} /> {MARKET_SIGNAL[s].label}{" "}
              <strong className="text-2xl">
                <CountUp to={counts[s]} />
              </strong>
            </li>
          ))}
          <li className="text-muted">
            표본 적음{" "}
            <strong className="text-2xl">
              <CountUp to={counts.low} />
            </strong>
          </li>
        </ul>
      </div>

      <InView>
        <ul className="mt-10 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.map(({ d, c }, k) => (
            <li key={d.code}>
              <Link
                href={href({ gu: data.gu, dong: d.code, ind: String(ind) })}
                className="fade-up group flex h-full flex-col rounded-[var(--radius-card)] bg-surface p-6 transition-colors hover:bg-[#e2e5e2]"
                style={{ ["--i" as string]: Math.min(k, 12) * 0.5 }}
              >
                <span className="flex items-center justify-between gap-3">
                  <span className="text-xl font-bold">{d.name}</span>
                  {c && c[0] !== "low" ? (
                    <span className="flex items-center gap-2 font-semibold">
                      <SignalShape s={c[0]} size={12} />{" "}
                      {MARKET_SIGNAL[c[0]].label}
                    </span>
                  ) : (
                    <LowBadge />
                  )}
                </span>
                {c && c[0] !== "low" ? (
                  <span className="mt-3 text-[0.9375rem] text-muted">
                    위험가중치 {c[1].toFixed(2)} · 평균 폐업률 {c[2]}% · {c[3]}
                    개 분기
                  </span>
                ) : (
                  <span className="mt-3 text-[0.9375rem] text-muted">
                    관측 {c?.[1]}개 분기라 판정하지 않습니다
                  </span>
                )}
                <span className="mt-5 flex items-center gap-1.5">
                  {d.ind.map((x, j) =>
                    x && x[0] !== "low" ? (
                      <span
                        key={META.industries[j].name}
                        title={`${META.industries[j].label} ${MARKET_SIGNAL[x[0]].label}`}
                      >
                        <SignalShape s={x[0]} size={9} />
                      </span>
                    ) : null,
                  )}
                  <span className="ml-auto flex items-center gap-1 text-sm font-semibold text-muted transition-colors group-hover:text-fg group-focus-visible:text-fg">
                    업종 보기 <Arrow />
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </InView>
    </div>
  );
}

/* ── 3단계: 행정동 → 업종 상세 ─────────────────────── */
function DongLevel({
  data,
  dong,
  ind,
  svc,
}: {
  data: GuData;
  dong: GuData["dongs"][number];
  ind: number;
  svc?: string;
}) {
  const bySvc = data.series[dong.code] ?? {};
  const names = new Map(META.services.map((s) => [s.code, s]));
  const list = Object.entries(bySvc)
    .map(([code, rows]) => {
      const ok = rows.filter(
        (r): r is NonNullable<Row> => !!r && r[0] > LOW_STORES && r[3] != null,
      );
      const last = [...rows].reverse().find(Boolean) ?? null;
      const w =
        ok.length >= 8
          ? ok.reduce((s, r) => s + (r[3] ?? 0), 0) / ok.length
          : null;
      return {
        code,
        name: names.get(code)?.name ?? code,
        ind: names.get(code)?.ind,
        rows,
        last,
        w,
      };
    })
    .filter((x) => x.ind === ind)
    .sort((a, b) => (b.w ?? -1) - (a.w ?? -1));
  const pick = list.find((x) => x.code === svc) ?? list[0];

  return (
    <div>
      <h3 className="title">
        {dong.name} · {META.industries[ind].label}
      </h3>
      {!list.length ? (
        <p className="lead mt-6 text-muted">
          이 행정동에는 {META.industries[ind].label} 업종 통계가 없습니다.
          위에서 다른 산업을 골라 보세요.
        </p>
      ) : (
        <div className="mt-10 grid gap-10 lg:grid-cols-[1fr_1.5fr] lg:gap-16">
          <ul className="grid content-start gap-2">
            {list.map((x) => (
              <li key={x.code}>
                <Link
                  href={href({
                    gu: data.gu,
                    dong: dong.code,
                    ind: String(ind),
                    svc: x.code,
                  })}
                  aria-current={x.code === pick.code ? "true" : undefined}
                  className="flex items-center justify-between gap-4 rounded-xl px-4 py-3 transition-colors hover:bg-surface aria-[current=true]:bg-night aria-[current=true]:text-white"
                >
                  <span className="font-semibold">{x.name}</span>
                  {x.w != null ? (
                    <span className="flex items-center gap-2 text-[0.9375rem]">
                      <SignalShape s={signalOf(x.w)} size={11} />{" "}
                      {MARKET_SIGNAL[signalOf(x.w)].label}
                    </span>
                  ) : (
                    <LowBadge />
                  )}
                </Link>
              </li>
            ))}
          </ul>
          <ServiceChart
            key={pick.code}
            name={pick.name}
            rows={pick.rows}
            w={pick.w}
          />
        </div>
      )}
    </div>
  );
}

function ServiceChart({
  name,
  rows,
  w,
}: {
  name: string;
  rows: Row[];
  w: number | null;
}) {
  const max = Math.max(5, ...rows.map((r) => r?.[1] ?? 0));
  const last = [...rows].reverse().find(Boolean);
  return (
    <InView className="fade-up order-first min-w-0 rounded-[var(--radius-card)] bg-surface p-6 sm:p-10 lg:order-none">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <h4 className="text-2xl font-bold">{name}</h4>
          <p className="mt-1 text-muted">분기별 폐업률 · 점포 수</p>
        </div>
        <dl className="flex gap-8">
          <div>
            <dt className="text-sm text-muted">최근 폐업률</dt>
            <dd className="text-3xl font-bold">
              <CountUp to={last?.[1] ?? 0} decimals={1} />%
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted">위험가중치</dt>
            <dd className="text-3xl font-bold">
              {w != null ? <CountUp to={w} decimals={2} /> : "–"}
            </dd>
          </div>
        </dl>
      </div>
      <ol className="mt-10 flex h-56 items-end gap-1.5 sm:gap-3">
        {rows.map((r, k) => {
          const low = !r || r[0] <= LOW_STORES;
          return (
            <li
              key={META.quarters[k]}
              className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1.5"
            >
              <span className="hidden text-[0.8125rem] font-semibold sm:block">
                {r ? r[1] : "–"}
              </span>
              <span
                className={`bar bar-v w-full rounded-t-md ${low ? "bg-[#c9cec9]" : "bg-lamp-red"}`}
                style={{
                  height: `${((r?.[1] ?? 0) / max) * 75 + 2}%`,
                  ["--b" as string]: k,
                }}
                title={low ? "표본 적음" : undefined}
              />
              <span
                className={`text-[0.8125rem] text-muted ${k % 2 ? "invisible sm:visible" : ""}`}
              >
                {META.quarters[k].slice(2).replace(" ", "")}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="mt-6 text-sm text-muted">
        회색 막대는 점포 5개 이하 분기입니다. 폐업률이 0 · 33 · 67%처럼 계단값이
        되니 크게 해석하지 마세요. 점포 수는 프랜차이즈를 뺀 수입니다(목업
        데이터 한계).
      </p>
    </InView>
  );
}
