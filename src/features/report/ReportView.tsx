"use client";
// F-LLM: 진단 결과 기반 AI 리포트. 하단 한계 고지(F-LLM-05)는 제거할 수 없다.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Arrow } from "@/components/icons";
import { GRADE, SIGNAL_STORAGE_KEY, type Signal } from "@/shared/types/signal";
import { buildReport, checkNumbers } from "./domain/buildReport";
import { SAMPLE_SIGNAL } from "./sample";

const LEVEL_COLOR = {
  GREEN: "var(--color-signal-green)",
  YELLOW: "var(--color-signal-yellow)",
  RED: "var(--color-signal-red)",
} as const;

/** 목업 상담: 진단 결과에 있는 값으로만 답한다(F-LLM-03). */
function answers(s: Signal): [string, string][] {
  const first = s.solutions[0];
  return [
    [
      "왜 이 등급이 나왔나요?",
      `매출 지수가 ${s.sales_index.join(" → ")}로 움직였고, ${s.place.dong} ${s.place.service}의 폐업률이 같은 업종 안에서 ${Math.round(s.percentile * 100)}% 위치에 있어서입니다. 두 값을 함께 보고 등급을 정합니다.`,
    ],
    [
      "지원사업은 어디서 신청하나요?",
      first
        ? `${first.title}는 ${first.agency}에서 다룹니다. 대상은 “${first.target}”입니다. 한도·금리처럼 원문에 없는 값은 ‘확인 필요’로 두었으니 기관에 직접 확인하세요.`
        : "지금 등급에서는 추천한 지원사업이 없습니다.",
    ],
    [
      "다음에는 무엇을 보면 되나요?",
      `석 달 뒤 같은 방법으로 다시 진단해 매출 지수의 흐름을 보세요. 동네 흐름은 상권 지도에서 ${s.place.gu} → ${s.place.dong} 순서로 확인할 수 있습니다.`,
    ],
  ];
}

export default function ReportView() {
  const [signal, setSignal] = useState<Signal | null>(null);
  const [sample, setSample] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem(SIGNAL_STORAGE_KEY);
    if (raw) setSignal(JSON.parse(raw));
    setReady(true);
  }, []);

  const s = signal ?? (sample ? SAMPLE_SIGNAL : null);

  return (
    <main>
      <section className="bg-surface">
        <div className="frame grid gap-10 pt-14 pb-10 lg:grid-cols-[1fr_1fr] lg:items-end lg:gap-24 lg:pt-20">
          <h1 className="title">
            <span className="rise-line">
              <span>AI 진단 리포트</span>
            </span>
          </h1>
          <p className="lead fade-up">
            진단 결과를 쉬운 말로 풀어 씁니다. 리포트의 숫자와 사업명은 진단
            결과와 공고 원문에 있는 값인지 대조한 뒤에 보여 드립니다.
          </p>
        </div>
      </section>

      {!ready ? null : s ? (
        <Report key={sample ? "sample" : "mine"} s={s} isSample={!signal} />
      ) : (
        <section className="frame grid gap-10 py-24 lg:grid-cols-[1fr_auto] lg:items-end lg:py-32">
          <div>
            <h2 className="title max-w-[36rem]">아직 진단 결과가 없습니다</h2>
            <p className="lead mt-6 max-w-[36rem]">
              리포트는 사업장 진단 결과로 씁니다. 진단을 먼저 하거나, 예시
              결과로 어떤 리포트가 나오는지 볼 수 있습니다.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/diagnosis" className="btn btn-primary">
              진단하러 가기 <Arrow />
            </Link>
            <button
              type="button"
              onClick={() => setSample(true)}
              className="btn btn-quiet"
            >
              예시 리포트 보기
            </button>
          </div>
        </section>
      )}
    </main>
  );
}

function Report({ s, isSample }: { s: Signal; isSample: boolean }) {
  const sections = useMemo(() => buildReport(s), [s]);
  const full = sections.map((x) => x.body).join("\n");
  const off = useMemo(() => checkNumbers(full, s), [full, s]);
  const total = full.length;
  const [shown, setShown] = useState(0);
  const [asked, setAsked] = useState<number[]>([]);
  const qa = answers(s);
  const g = GRADE[s.risk_level];

  // 스트리밍 흉내: 첫 글자는 곧바로, 이후 한 번에 몇 글자씩
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(total);
      return;
    }
    setShown(0);
    const t = setInterval(() => {
      setShown((n) => {
        if (n >= total) {
          clearInterval(t);
          return n;
        }
        return n + 3;
      });
    }, 24);
    return () => clearInterval(t);
  }, [total]);

  let left = shown;
  const done = shown >= total;

  return (
    <section
      aria-labelledby="report-h"
      className="frame grid gap-12 py-16 lg:grid-cols-[1.4fr_1fr] lg:gap-20 lg:py-24"
    >
      <article>
        <header className="flex flex-wrap items-center gap-4">
          <span
            className="grid size-16 place-items-center rounded-2xl text-4xl font-bold text-white"
            style={{ background: LEVEL_COLOR[s.risk_level] }}
          >
            {g.letter}
          </span>
          <div>
            <h2 id="report-h" className="text-2xl font-bold">
              {s.place.gu} {s.place.dong} · {s.place.service}
            </h2>
            <p className="text-muted">
              진단 등급 {g.letter} ({g.label}){isSample && " · 예시 결과"}
            </p>
          </div>
        </header>

        <div className="mt-12 grid gap-10" aria-live="polite" aria-busy={!done}>
          {sections.map((x) => {
            const take = Math.max(0, Math.min(x.body.length, left));
            left -= x.body.length + 1;
            if (take === 0 && !done) return null;
            const typing = take < x.body.length;
            return (
              <div key={x.heading} className="fade-up">
                <h3 className="text-xl font-bold">{x.heading}</h3>
                <p className="mt-3 text-[1.125rem] leading-[1.75] whitespace-pre-line">
                  {x.body.slice(0, take)}
                  {typing && (
                    <span className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-[3px] bg-fg" />
                  )}
                </p>
              </div>
            );
          })}
        </div>

        {!done && (
          <button
            type="button"
            onClick={() => setShown(total)}
            className="link-under mt-8 text-[0.9375rem] font-medium text-accent"
          >
            한 번에 보기
          </button>
        )}

        {/* F-LLM-05: 한계 고지. 지우지 않는다. */}
        <aside className="mt-16 rounded-[var(--radius-card)] bg-surface p-6 text-[0.9375rem] leading-relaxed sm:p-8">
          <h3 className="font-bold">이 리포트의 한계</h3>
          <p className="mt-2">
            이 리포트는 통계 모델의 추정을 풀어 쓴 것이며, 대출·지원 대상 여부를
            확정하지 않습니다. 원인 유형은 확정 진단이 아니라 확률로 본
            추정입니다. 지원사업의 한도·금리·기간은 반드시 공고 원문과 담당
            기관에서 확인하세요. 목업 화면이라 글은 실제 LLM 대신 템플릿으로
            썼습니다.
          </p>
        </aside>
      </article>

      <div className="grid content-start gap-6 lg:sticky lg:top-28 lg:self-start">
        <div className="rounded-[var(--radius-card)] bg-night p-6 text-on-night sm:p-8">
          <h3 className="font-bold">수치 대조</h3>
          {done ? (
            off.length === 0 ? (
              <p className="mt-2 text-on-night-muted">
                리포트에 나온 숫자가 모두 진단 결과와 공고 원문에 있습니다.
              </p>
            ) : (
              <p className="mt-2 text-lamp-yellow">
                근거에 없는 숫자 {off.join(", ")}가 있어 다시 씁니다.
              </p>
            )
          ) : (
            <p className="mt-2 text-on-night-muted">
              글을 다 쓰면 숫자를 근거와 대조합니다…
            </p>
          )}
          <ul className="mt-6 grid gap-2 text-[0.9375rem]">
            <li className="flex justify-between gap-4">
              <span className="text-on-night-muted">매출 지수</span>
              <span>{s.sales_index.join(" → ")}</span>
            </li>
            <li className="flex justify-between gap-4">
              <span className="text-on-night-muted">보정 위험 확률</span>
              <span>{Math.round(s.level_probs.RED * 100)}%</span>
            </li>
            <li className="flex justify-between gap-4">
              <span className="text-on-night-muted">위험 점수</span>
              <span>{s.score} / 100</span>
            </li>
            <li className="flex justify-between gap-4">
              <span className="text-on-night-muted">근거 문서</span>
              <span>
                {s.solutions.map((d) => d.source_doc_id).join(", ") || "없음"}
              </span>
            </li>
          </ul>
        </div>

        <div className="rounded-[var(--radius-card)] bg-surface p-6 sm:p-8">
          <h3 className="font-bold">이어서 물어보기</h3>
          <ul className="mt-4 grid gap-2">
            {qa.map(([q], k) => (
              <li key={q}>
                <button
                  type="button"
                  disabled={asked.includes(k)}
                  onClick={() => setAsked((a) => [...a, k])}
                  className="w-full rounded-xl bg-bg px-4 py-3 text-left font-medium transition-colors hover:bg-[#e2e5e2] disabled:text-muted"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-4 grid gap-3" aria-live="polite">
            {asked.map((k) => (
              <div key={qa[k][0]} className="fade-up rounded-xl bg-bg p-4">
                <p className="text-sm font-semibold text-muted">{qa[k][0]}</p>
                <p className="mt-1">{qa[k][1]}</p>
              </div>
            ))}
          </div>
        </div>

        <Link href="/diagnosis" className="btn btn-quiet justify-center">
          다시 진단하기
        </Link>
      </div>
    </section>
  );
}
