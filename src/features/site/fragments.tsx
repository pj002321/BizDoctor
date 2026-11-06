/**
 * 실제 화면 조각. 랜딩·서비스 안내에서 "이 서비스가 무엇을 보여 주나"를 그림 대신 보여 준다.
 * 막대와 수치는 화면에 들어오면 차오른다(InView · CountUp).
 * 상권 수치는 data/seoul.json(실제 CSV 추출본), 진단·리포트는 "예시"라고 적은 표본 값이다.
 */

import CountUp from "@/components/CountUp";
import InView from "@/components/InView";
import data from "./data/seoul.json";

const panel = "rounded-[var(--radius-card)] bg-bg p-6 sm:p-8";

/* ── 사업장 진단 등급 (예시) ─────────────────────────────── */
const SAMPLE_INDEX = [100, 94, 81];
const SAMPLE_CAUSES = [
  ["단기 매출 정체형", 41],
  ["원가 상승 부담형", 33],
  ["정상 유지형", 26],
] as const;

export function GradeFragment() {
  return (
    <InView className={panel}>
      <div className="flex items-center gap-4">
        <span className="grid size-14 shrink-0 place-items-center rounded-xl bg-signal-yellow text-3xl font-bold text-white">
          B
        </span>
        <div>
          <p className="text-xl font-bold">관찰 필요</p>
          <p className="text-sm text-muted">
            예시 · 마포구 서교동 커피-음료 · 보정 위험확률 18% · 확신 낮음
          </p>
        </div>
      </div>
      <p className="mt-6 text-sm font-semibold">
        최근 3개월 매출 지수 (1개월차 = 100)
      </p>
      <div className="mt-3 flex items-end gap-3">
        {SAMPLE_INDEX.map((v, i) => (
          <div key={v} className="flex flex-1 flex-col items-center gap-1">
            <span className="text-sm font-semibold">
              <CountUp to={v} />
            </span>
            <span
              className="bar bar-v w-full rounded-t-md bg-fg"
              style={{
                height: `${v * 0.64}px`,
                opacity: 0.45 + i * 0.27,
                ["--b" as string]: i,
              }}
            />
            <span className="text-[0.8125rem] text-muted">{i + 1}개월차</span>
          </div>
        ))}
      </div>
      <p className="mt-6 text-sm font-semibold">추정 원인</p>
      <ul className="mt-2 grid gap-2">
        {SAMPLE_CAUSES.map(([name, p], k) => (
          <li
            key={name}
            className="grid grid-cols-[8.5rem_1fr_2.5rem] items-center gap-3 text-sm"
          >
            <span>{name}</span>
            <span className="h-2 rounded-full bg-surface">
              <span
                className="bar block h-full rounded-full bg-signal-yellow"
                style={{ width: `${p}%`, ["--b" as string]: k + 3 }}
              />
            </span>
            <span className="text-right">
              <CountUp to={p} />%
            </span>
          </li>
        ))}
      </ul>
    </InView>
  );
}

/* ── 지원사업 추천 (단기 매출 정체형 기준, 실제 문서 제목) ───────── */
const SOLUTIONS = [
  ["일반경영안정자금", "소상공인 정책자금 · 운전자금"],
  ["경영안정 바우처 및 디지털 전환 지원", "고정비 보전 · 온라인 판로"],
  ["청년 소상공인 특화 자금", "만 39세 이하 대표자"],
] as const;

export function SolutionsFragment() {
  return (
    <div data-ui className={panel}>
      <p className="text-sm text-muted">
        추정 원인 “단기 매출 정체형”에 맞는 사업
      </p>
      <ul className="mt-4 grid gap-2">
        {SOLUTIONS.map(([t, d]) => (
          <li key={t} className="rounded-xl bg-surface-2 p-4">
            <p className="font-semibold">{t}</p>
            <p className="text-sm text-muted">{d}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── AI 리포트 (예시) ─────────────────────────────────── */
export function ReportFragment() {
  return (
    <div data-ui className={panel}>
      <p className="text-sm text-muted">AI 진단 리포트 · 예시</p>
      <p className="mt-3 text-lg font-bold">
        석 달 사이 매출 지수가 100에서 81로 내려왔습니다
      </p>
      <p className="mt-2 text-[0.9375rem] leading-relaxed">
        같은 행정동 커피-음료 업종의 폐업률은 업종 안에서 상위 33% 수준입니다.
        먼저 고정비를 줄일 수 있는 경영안정 바우처를 확인해 보세요.
      </p>
      <p className="mt-4 rounded-xl bg-surface-2 p-3 text-[0.8125rem] leading-relaxed text-muted">
        이 리포트의 수치와 사업명은 진단 결과와 공고 원문에서만 가져왔습니다.
        원인 유형은 확정 진단이 아닌 추정입니다.
      </p>
    </div>
  );
}

/* ── 업종별 평균 폐업률 순위 ─────────────────────────────── */
export function RankingFragment() {
  const max = data.ranking[0].rate;
  return (
    <InView className={panel}>
      <div className="flex items-baseline justify-between gap-4 text-sm text-muted">
        <span>업종별 평균 폐업률 상위 8</span>
        <span>2023 Q1 – 2025 Q3</span>
      </div>
      <ol className="mt-4 grid gap-2.5">
        {data.ranking.map((r, k) => (
          <li
            key={r.name}
            className="grid grid-cols-[6.5rem_1fr_3rem] items-center gap-3 text-sm"
          >
            <span className="truncate">{r.name}</span>
            <span className="h-3 rounded-full bg-surface">
              <span
                className="bar block h-full rounded-full bg-lamp-red"
                style={{
                  width: `${(r.rate / max) * 100}%`,
                  ["--b" as string]: k,
                }}
              />
            </span>
            <span className="text-right font-semibold">
              <CountUp to={r.rate} decimals={2} />%
            </span>
          </li>
        ))}
      </ol>
    </InView>
  );
}
