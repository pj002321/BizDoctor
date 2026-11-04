"use client";
import Link from "next/link";
import { useMemo, useState, useTransition } from "react";
import CountUp from "@/components/CountUp";
import InView from "@/components/InView";
import { Arrow } from "@/components/icons";
import {
  GRADE,
  RISK_TYPE_LEVEL,
  type RiskLevel,
  type RiskType,
  SIGNAL_STORAGE_KEY,
  type Signal,
} from "@/shared/types/signal";
import catalog from "./data/catalog.json";
import { runDiagnosis } from "./server/runDiagnosis";

const GU = [...new Set(catalog.dongs.map((d) => d.gu))].sort((a, b) =>
  a.localeCompare(b, "ko"),
);
const SERVICE_GROUPS = Object.entries(
  catalog.services.reduce<Record<string, typeof catalog.services>>((m, s) => {
    const k = s.kosis || "기타";
    m[k] ??= [];
    m[k].push(s);
    return m;
  }, {}),
);
const LEVEL_COLOR: Record<RiskLevel, string> = {
  GREEN: "var(--color-signal-green)",
  YELLOW: "var(--color-signal-yellow)",
  RED: "var(--color-signal-red)",
};
const MONTHS = ["1개월차", "2개월차", "3개월차"];
const SAMPLE = {
  gu: "마포구",
  dong: "11440660",
  service: "CS100010",
  sales: ["21,400,000", "19,800,000", "17,350,000"],
};

const parse = (s: string) => Number(s.replace(/[^\d]/g, ""));
const fmt = (s: string) => {
  const n = parse(s);
  return n ? n.toLocaleString("ko-KR") : "";
};
const pct = (v: number) => `${Math.round(v * 100)}%`;
const typeName = (t: RiskType) => t.replaceAll("_", " ");

export default function DiagnosisView() {
  const [gu, setGu] = useState("");
  const [dong, setDong] = useState("");
  const [service, setService] = useState("");
  const [sales, setSales] = useState(["", "", ""]);
  const [error, setError] = useState<string | null>(null);
  const [signal, setSignal] = useState<Signal | null>(null);
  const [pending, start] = useTransition();

  const dongs = useMemo(
    () =>
      catalog.dongs
        .filter((d) => d.gu === gu)
        .sort((a, b) => a.name.localeCompare(b.name, "ko")),
    [gu],
  );
  const nums = sales.map(parse);
  const preview =
    nums[0] > 0
      ? nums.map((v) => (v > 0 ? Math.round((v / nums[0]) * 1000) / 10 : null))
      : null;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    start(async () => {
      const res = await runDiagnosis({
        dongCode: dong,
        serviceCode: service,
        sales: nums,
      });
      if (!res.ok) return setError(res.error);
      setSignal(res.signal);
      sessionStorage.setItem(SIGNAL_STORAGE_KEY, JSON.stringify(res.signal));
      requestAnimationFrame(() =>
        document
          .getElementById("result")
          ?.scrollIntoView({ behavior: "smooth" }),
      );
    });
  };

  const fillSample = () => {
    setGu(SAMPLE.gu);
    setDong(SAMPLE.dong);
    setService(SAMPLE.service);
    setSales(SAMPLE.sales);
    setError(null);
  };

  const field =
    "mt-2 block w-full rounded-xl bg-bg px-4 py-3.5 text-[1.0625rem] transition-colors focus:outline-3 focus:outline-offset-2 focus:outline-accent";

  return (
    <main>
      {/* ── 입력 ─────────────────────────────── */}
      <section className="bg-surface">
        <div className="frame grid gap-14 py-14 lg:grid-cols-[1fr_1.15fr] lg:gap-24 lg:py-20">
          <div>
            <h1 className="title">
              <span className="rise-line">
                <span>내 가게 진단 등급</span>
              </span>
            </h1>
            <p className="lead fade-up mt-6 max-w-[34rem]">
              동네와 업종을 고르고 최근 석 달 매출을 넣으면, 같은 동네 같은
              업종의 폐업 통계와 견줘 A · B · C 등급과 추정 원인을 보여
              드립니다.
            </p>
            <dl
              className="fade-up mt-12 grid gap-6"
              style={{ ["--i" as string]: 1 }}
            >
              <div>
                <dt className="font-bold">매출은 지수로만 씁니다</dt>
                <dd className="mt-1 text-muted">
                  1개월차를 100으로 놓은 비율만 계산에 쓰고, 금액은 저장하지
                  않습니다.
                </dd>
              </div>
              <div>
                <dt className="font-bold">동네 전체 결과와는 다릅니다</dt>
                <dd className="mt-1 text-muted">
                  상권 지도는 동네 전체를, 진단 등급은 내 가게 하나를 봅니다.
                </dd>
              </div>
            </dl>
          </div>

          <form
            onSubmit={submit}
            className="fade-up rounded-[var(--radius-card)] bg-surface-2 p-6 sm:p-10"
            style={{ ["--i" as string]: 2 }}
            noValidate
          >
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-xl font-bold">진단 정보</h2>
              <button
                type="button"
                onClick={fillSample}
                className="link-under text-[0.9375rem] font-medium text-accent"
              >
                예시로 채우기
              </button>
            </div>

            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              <label className="block">
                <span className="font-semibold">자치구</span>
                <select
                  className={field}
                  value={gu}
                  onChange={(e) => {
                    setGu(e.target.value);
                    setDong("");
                  }}
                  required
                >
                  <option value="">고르세요</option>
                  {GU.map((g) => (
                    <option key={g}>{g}</option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="font-semibold">행정동</span>
                <select
                  className={field}
                  value={dong}
                  onChange={(e) => setDong(e.target.value)}
                  disabled={!gu}
                  required
                >
                  <option value="">{gu ? "고르세요" : "자치구를 먼저"}</option>
                  {dongs.map((d) => (
                    <option key={d.code} value={d.code}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block sm:col-span-2">
                <span className="font-semibold">업종</span>
                <select
                  className={field}
                  value={service}
                  onChange={(e) => setService(e.target.value)}
                  required
                >
                  <option value="">고르세요</option>
                  {SERVICE_GROUPS.map(([k, list]) => (
                    <optgroup key={k} label={k}>
                      {list.map((s) => (
                        <option key={s.code} value={s.code}>
                          {s.name}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </label>
            </div>

            <fieldset className="mt-8">
              <legend className="font-semibold">최근 3개월 매출 (원)</legend>
              <div className="mt-2 grid gap-3 sm:grid-cols-3">
                {MONTHS.map((m, k) => (
                  <label key={m} className="block">
                    <span className="text-sm text-muted">{m}</span>
                    <input
                      className={`${field} mt-1 text-right tabular-nums`}
                      inputMode="numeric"
                      autoComplete="off"
                      placeholder="0"
                      value={sales[k]}
                      onChange={(e) =>
                        setSales((s) =>
                          s.map((v, j) => (j === k ? fmt(e.target.value) : v)),
                        )
                      }
                      aria-describedby="sales-note"
                    />
                  </label>
                ))}
              </div>
              <p id="sales-note" className="mt-3 text-sm text-muted">
                {preview ? (
                  <>
                    계산에 쓰는 값:{" "}
                    <strong className="text-fg">
                      {preview.map((v) => (v == null ? "–" : v)).join(" → ")}
                    </strong>{" "}
                    (1개월차 = 100)
                  </>
                ) : (
                  "넣는 즉시 1개월차 = 100인 지수로 바뀝니다. 금액은 저장하지 않습니다."
                )}
              </p>
            </fieldset>

            {error && (
              <p
                role="alert"
                className="mt-6 rounded-xl bg-[color-mix(in_srgb,var(--color-signal-red)_10%,white)] p-4 font-medium text-signal-red"
              >
                {error}
              </p>
            )}

            <button
              type="submit"
              className="btn btn-primary mt-8 w-full justify-center disabled:opacity-60"
              disabled={pending}
            >
              {pending ? (
                "진단하는 중…"
              ) : (
                <>
                  진단 등급 보기 <Arrow />
                </>
              )}
            </button>
          </form>
        </div>
      </section>

      {/* ── 결과 ─────────────────────────────── */}
      {signal ? (
        <Result
          key={
            JSON.stringify(signal.sales_index) +
            signal.place.dong +
            signal.place.service
          }
          s={signal}
        />
      ) : (
        <Empty />
      )}
    </main>
  );
}

function Empty() {
  return (
    <section className="frame py-24 lg:py-32">
      <h2 className="title max-w-[36rem]">결과는 여기에 나옵니다</h2>
      <p className="lead mt-6 max-w-[36rem] text-muted">
        진단 등급, 보정된 위험 확률, 추정 원인, 우리 동네 안에서의 위치, 맞는
        지원사업 세 가지가 한 화면에 정리됩니다.
      </p>
    </section>
  );
}

function Result({ s }: { s: Signal }) {
  const g = GRADE[s.risk_level];
  const color = LEVEL_COLOR[s.risk_level];
  const top = Math.max(1, Math.round((1 - s.percentile) * 100));
  const types = (Object.keys(s.type_probs) as RiskType[]).sort(
    (a, b) => s.type_probs[b] - s.type_probs[a],
  );

  return (
    <section
      id="result"
      aria-labelledby="result-h"
      className="frame py-20 lg:py-28"
    >
      <h2 id="result-h" className="sr-only">
        진단 결과
      </h2>

      {/* 등급 */}
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div
          className="fade-up rounded-[var(--radius-card)] p-8 text-white sm:p-12"
          style={{ background: color }}
        >
          <p className="text-lg font-medium opacity-90">
            {s.place.gu} {s.place.dong} · {s.place.service}
          </p>
          <div className="mt-8 flex items-end gap-6">
            <span className="text-[clamp(6rem,14vw,10rem)] leading-[0.8] font-bold tracking-[-0.06em]">
              {g.letter}
            </span>
            <div className="pb-2">
              <p className="text-3xl font-bold">{g.label}</p>
              {s.low_confidence && (
                <p className="mt-2 inline-block rounded-full bg-white/20 px-3 py-1 text-sm font-semibold">
                  확신 낮음
                </p>
              )}
            </div>
          </div>
          <p className="mt-10 text-lg">
            위험 점수{" "}
            <strong className="text-2xl">
              <CountUp to={s.score} />
            </strong>{" "}
            / 100
          </p>
        </div>

        <InView className="fade-up rounded-[var(--radius-card)] bg-surface p-8 sm:p-10">
          <h3 className="text-xl font-bold">보정한 등급 확률</h3>
          <p className="mt-1 text-[0.9375rem] text-muted">
            학습 데이터의 위험군 비중(30%)을 서울 실제 비중(약 14%)으로 되돌린
            값입니다.
          </p>
          <ul className="mt-6 grid gap-4">
            {(["GREEN", "YELLOW", "RED"] as const).map((l, k) => (
              <li
                key={l}
                className="grid grid-cols-[6.5rem_1fr_3.5rem] items-center gap-3"
              >
                <span className="font-semibold">
                  {GRADE[l].letter} · {GRADE[l].label}
                </span>
                <span className="h-3 rounded-full bg-bg">
                  <span
                    className="bar block h-full rounded-full"
                    style={{
                      width: pct(s.level_probs[l]),
                      background: LEVEL_COLOR[l],
                      ["--b" as string]: k,
                    }}
                  />
                </span>
                <span className="text-right font-bold">
                  <CountUp to={Math.round(s.level_probs[l] * 100)} />%
                </span>
              </li>
            ))}
          </ul>
          <h3 className="mt-10 text-xl font-bold">최근 3개월 매출 지수</h3>
          <div className="mt-4 flex items-end gap-4">
            {s.sales_index.map((v, k) => (
              <div
                key={MONTHS[k]}
                className="flex flex-1 flex-col items-center gap-1.5"
              >
                <span className="font-bold">
                  <CountUp to={v} decimals={v % 1 ? 1 : 0} />
                </span>
                <span
                  className="bar bar-v w-full rounded-t-md bg-fg"
                  style={{
                    height: `${Math.min(v, 160) * 0.8}px`,
                    opacity: 0.4 + k * 0.3,
                    ["--b" as string]: k,
                  }}
                />
                <span className="text-sm text-muted">{MONTHS[k]}</span>
              </div>
            ))}
          </div>
        </InView>
      </div>

      {/* 원인과 동네 */}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <InView className="rounded-[var(--radius-card)] bg-surface p-8 sm:p-10">
          <h3 className="text-xl font-bold">추정 원인</h3>
          <p className="mt-1 text-[0.9375rem] text-muted">
            확정 진단이 아닙니다. 일부 유형은 지금 모델로 가려내기 어려워
            확률로만 보여 드립니다.
          </p>
          <p className="mt-6 text-2xl font-bold">
            {typeName(s.risk_type)}{" "}
            <span className="text-lg font-semibold text-muted">
              (같은 등급 안에서 {pct(s.risk_type_confidence)})
            </span>
          </p>
          <ul className="mt-6 grid gap-3">
            {types.map((t, k) => (
              <li
                key={t}
                className={`grid grid-cols-[9rem_1fr_3rem] items-center gap-3 text-[0.9375rem] ${t === s.risk_type ? "font-bold" : ""}`}
              >
                <span>{typeName(t)}</span>
                <span className="h-2.5 rounded-full bg-bg">
                  <span
                    className="bar block h-full rounded-full"
                    style={{
                      width: pct(s.type_probs[t]),
                      background: LEVEL_COLOR[RISK_TYPE_LEVEL[t]],
                      ["--b" as string]: k,
                    }}
                  />
                </span>
                <span className="text-right">{pct(s.type_probs[t])}</span>
              </li>
            ))}
          </ul>
        </InView>

        <InView className="rounded-[var(--radius-card)] bg-night p-8 text-on-night sm:p-10">
          <h3 className="text-xl font-bold">우리 동네 안에서의 위치</h3>
          <p className="mt-6 text-[clamp(2.5rem,5vw,3.75rem)] leading-tight font-bold tracking-[-0.04em]">
            상위 <CountUp to={top} />%
          </p>
          <p className="mt-3 text-on-night-muted">
            서울 {s.place.service} 업종이 있는 행정동 가운데 {s.place.dong}의
            폐업률이 어디쯤인지입니다. 높을수록 폐업이 잦은 동네입니다. (
            {s.as_of} 기준, 이 분기 폐업률 {s.close_rate}%)
          </p>
          <div className="relative mt-8 h-3 rounded-full bg-white/15">
            <span
              className="bar absolute inset-y-0 left-0 rounded-full bg-lamp-yellow"
              style={{ width: pct(s.percentile) }}
            />
          </div>
          <div className="mt-2 flex justify-between text-sm text-on-night-muted">
            <span>폐업 적음</span>
            <span>폐업 잦음</span>
          </div>
        </InView>
      </div>

      {/* 지원사업 */}
      <div className="mt-24">
        <h3 className="title">맞는 지원사업</h3>
        {s.solutions.length ? (
          <ul className="mt-10 grid gap-4 lg:grid-cols-3">
            {s.solutions.map((d, k) => (
              <li
                key={d.source_doc_id}
                className="fade-up flex flex-col rounded-[var(--radius-card)] bg-surface p-8"
                style={{ ["--i" as string]: k }}
              >
                <p className="text-sm text-muted">{d.agency}</p>
                <p className="mt-2 text-xl font-bold">{d.title}</p>
                <p className="mt-3">{d.summary}</p>
                <dl className="mt-6 grid gap-2 text-[0.9375rem]">
                  {[
                    ["대상", d.target],
                    ["한도", d.limit],
                    ["금리", d.rate],
                    ["기간", d.period],
                  ].map(([k2, v]) => (
                    <div key={k2} className="grid grid-cols-[3rem_1fr] gap-2">
                      <dt className="font-semibold">{k2}</dt>
                      <dd className={v === "확인 필요" ? "text-muted" : ""}>
                        {v}
                      </dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        ) : (
          <p className="lead mt-6 max-w-[40rem]">
            지금은 안정 등급이라 추천할 긴급 지원사업이 없습니다. 석 달 뒤 다시
            진단해 흐름을 확인해 보세요.
          </p>
        )}
      </div>

      <div className="mt-16 flex flex-wrap items-center gap-3">
        <Link href="/report" className="btn btn-primary">
          AI 리포트 받기 <Arrow />
        </Link>
        <Link
          href={`/market?gu=${encodeURIComponent(s.place.gu)}`}
          className="btn btn-quiet"
        >
          {s.place.gu} 상권 지도 보기
        </Link>
      </div>
      <p className="mt-8 max-w-[48rem] text-sm text-muted">
        목업 화면입니다. 등급과 원인은 실제 모델 대신 같은 입출력 모양의
        규칙으로 계산했고, 사전확률 보정은 실제 서비스와 같은 방식으로
        적용했습니다. 결과는 대출·지원 대상 여부를 확정하지 않습니다.
      </p>
    </section>
  );
}
