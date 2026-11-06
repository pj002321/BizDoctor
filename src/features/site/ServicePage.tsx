import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { Arrow, MARKET_SIGNAL, SignalShape } from "@/components/icons";
import Lamps from "@/components/Lamps";
import { GradeFragment, RankingFragment, ReportFragment } from "./fragments";
import TrendChart from "./TrendChart";

const i = (n: number) => ({ ["--i" as string]: n });

const GRADES = [
  ["A", "안정", "var(--color-signal-green)"],
  ["B", "관찰 필요", "var(--color-signal-yellow)"],
  ["C", "위험", "var(--color-signal-red)"],
] as const;

const RISK_TYPES = [
  ["정상 유지형", "A", "—"],
  [
    "단기 매출 정체형",
    "B",
    "일반경영안정자금 · 경영안정 바우처 · 청년 소상공인 특화 자금",
  ],
  [
    "원가 상승 부담형",
    "B",
    "일반경영안정자금 · 이차보전 사업 · 경영안정 바우처",
  ],
  ["매출 폭락형", "C", "긴급경영안정자금"],
  [
    "고금리 과다채무형",
    "C",
    "새출발기금 · 신용회복위원회 채무조정 · 이차보전 사업",
  ],
  ["상권 침체 붕괴형", "C", "희망리턴패키지"],
] as const;

export default function ServicePage() {
  return (
    <main>
      {/* ── 머리: 시장 사진 위 ─────────────────── */}
      <section className="on-night relative isolate overflow-hidden bg-night text-on-night">
        <Image
          src="/photos/namdaemun-market-in-seoul-i.jpg"
          alt="남대문시장 상점가, 600주년 축제 현수막 아래로 오가는 사람들"
          fill
          priority
          sizes="100vw"
          className="photo-drift -z-10 object-cover object-[50%_60%]"
        />
        <div className="absolute inset-0 -z-10 bg-[rgb(18_21_19/0.74)]" />
        <div className="frame grid gap-10 pt-28 pb-16 lg:grid-cols-[1.1fr_1fr] lg:items-end lg:pt-40 lg:pb-20">
          <div>
            <Lamps className="fade-up" size="1.25rem" />
            <h1 className="display mt-8">
              <span className="rise-line">
                <span style={i(0)}>상권 신호등부터</span>
              </span>
              <span className="rise-line">
                <span style={i(1)}>지원사업 추천까지</span>
              </span>
            </h1>
          </div>
          <div className="fade-up" style={i(0)}>
            <p className="lead">
              상권 신호등은 동네를, 진단 등급은 내 가게를 봅니다. 두 결과는
              이름·색 범례·주소를 따로 써서 섞이지 않게 했습니다.
            </p>
            <nav aria-label="이 페이지 차례" className="mt-8">
              <ul className="flex flex-wrap gap-2">
                {[
                  ["#market", "상권 신호등"],
                  ["#trend", "산업 추이"],
                  ["#diagnosis", "사업장 진단"],
                  ["#solutions", "지원사업"],
                  ["#report", "AI 리포트"],
                  ["#limits", "계산 방법과 한계"],
                ].map(([h, l]) => (
                  <li key={h}>
                    <a
                      href={h}
                      className="inline-block rounded-full bg-white/14 px-4 py-2 text-[0.9375rem] font-medium transition-colors hover:bg-white/24"
                    >
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        </div>
      </section>

      {/* ── 상권 신호등 ─────────────────────────── */}
      <Chapter
        id="market"
        title="상권 신호등"
        lead="25개 자치구 지도에서 시작해 행정동 성적표, 업종별 11개 분기 추이로 좁혀 갑니다. 색은 업종 안에서 폐업률이 어디쯤인지를 평균한 위험가중치로 정합니다."
        href="/market"
        cta="상권 신호등 보기"
        aside={
          <figure className="relative aspect-[4/3] overflow-hidden rounded-[var(--radius-card)]">
            <Image
              src="/photos/gwangjang-market-seoul-01.jpg"
              alt="종로 광장시장 정문"
              fill
              sizes="(min-width: 1024px) 45vw, 100vw"
              className="object-cover"
            />
          </figure>
        }
      >
        <ul className="mt-8 grid gap-3">
          {(["g", "y", "r"] as const).map((s) => (
            <li key={s} className="flex items-center gap-3">
              <SignalShape s={s} size={14} />
              <span className="w-16 shrink-0 font-bold">
                {MARKET_SIGNAL[s].label}
              </span>
              <span className="text-muted">
                위험가중치 {MARKET_SIGNAL[s].rule}
              </span>
            </li>
          ))}
          <li className="flex items-center gap-3">
            <span className="w-[14px]" />
            <span className="w-16 shrink-0 font-bold text-muted">
              표본 적음
            </span>
            <span className="text-muted">
              점포 5개 이하 칸 · 폐업률이 계단값이 됩니다
            </span>
          </li>
        </ul>
      </Chapter>

      {/* ── 산업 추이 · 업종 순위 ─────────────────── */}
      <section
        id="trend"
        aria-labelledby="trend-h"
        className="bg-surface py-32 lg:py-44"
      >
        <div className="frame">
          <div className="grid gap-6 lg:grid-cols-[1fr_1fr] lg:items-end lg:gap-16">
            <h2 id="trend-h" className="title" data-reveal>
              산업 추이와 업종 순위
            </h2>
            <p className="lead text-muted" data-reveal style={i(1)}>
              음식점업은 분기마다 4% 안팎이 문을 닫고, 소매업은 2~3%대를
              오갑니다. 서울 전체 흐름 위에 내 업종이 어디 있는지 봅니다.
            </p>
          </div>
          <div className="mt-16 grid gap-6 lg:grid-cols-[1.3fr_1fr]">
            <div data-reveal style={i(1)}>
              <TrendChart />
            </div>
            <div data-reveal style={i(2)}>
              <RankingFragment />
            </div>
          </div>
        </div>
      </section>

      {/* ── 사업장 진단 ─────────────────────────── */}
      <Chapter
        id="diagnosis"
        title="사업장 진단 등급"
        lead="행정동 · 업종 · 최근 3개월 매출을 넣습니다. 매출은 1개월차 = 100인 지수로 바뀌고, 같은 동네 같은 업종의 통계와 함께 모델에 들어갑니다."
        href="/diagnosis"
        cta="진단 시작"
        aside={
          <div className="rounded-[var(--radius-card)] bg-surface p-5 sm:p-12">
            <GradeFragment />
          </div>
        }
      >
        <ul className="mt-8 flex flex-wrap gap-3">
          {GRADES.map(([g, l, c]) => (
            <li
              key={g}
              className="flex items-center gap-2.5 rounded-full bg-surface-2 py-2 pr-4 pl-2"
            >
              <span
                className="grid size-8 place-items-center rounded-full font-bold text-white"
                style={{ background: c }}
              >
                {g}
              </span>
              <span className="font-semibold">{l}</span>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-[0.9375rem] text-muted">
          ‘관찰 필요’는 확신이 낮을 때가 많아 배지를 함께 답니다.
        </p>
      </Chapter>

      {/* ── 지원사업 ─────────────────────────────── */}
      <section
        id="solutions"
        aria-labelledby="sol-h"
        className="on-night bg-night py-28 text-on-night lg:py-36"
      >
        <div className="frame">
          <div className="grid gap-6 lg:grid-cols-[1fr_1fr] lg:items-end lg:gap-16">
            <h2 id="sol-h" className="title" data-reveal>
              추정 원인에 맞는 지원사업
            </h2>
            <p className="lead text-on-night-muted" data-reveal style={i(1)}>
              위기 유형 태그가 붙은 공고를 먼저 세우고, 그 안에서 의미 검색과
              키워드 검색 순위를 합쳐 정렬합니다.
            </p>
          </div>
          <div className="mt-14" data-reveal style={i(2)}>
            <table className="w-full text-left">
              <caption className="sr-only">
                위기 유형별 진단 등급과 연결되는 지원사업
              </caption>
              <thead className="text-sm text-on-night-muted">
                <tr>
                  <th scope="col" className="pb-4 font-medium">
                    위기 유형
                  </th>
                  <th scope="col" className="pb-4 font-medium">
                    진단 등급
                  </th>
                  <th scope="col" className="pb-4 font-medium">
                    찾아 주는 사업
                  </th>
                </tr>
              </thead>
              <tbody>
                {RISK_TYPES.map(([t, g, s]) => (
                  <tr
                    key={t}
                    className="odd:bg-white/[0.06] [&>*:first-child]:rounded-l-xl [&>*:last-child]:rounded-r-xl"
                  >
                    <th
                      scope="row"
                      className="py-5 pr-4 pl-4 text-base font-bold sm:text-lg"
                    >
                      {t}
                    </th>
                    <td className="py-5 pr-4">{g}</td>
                    <td className="py-5 pr-4 text-[0.9375rem] text-on-night-muted sm:text-base">
                      {s}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── AI 리포트 ─────────────────────────────── */}
      <Chapter
        id="report"
        title="AI 리포트와 상담"
        lead="진단 결과를 쉬운 말로 풀어 씁니다. 리포트에 나오는 수치와 사업명은 진단 결과와 공고 원문에 있는 값인지 한 번 더 대조한 뒤에 내보냅니다."
        href="/report"
        cta="AI 리포트 보기"
        flip
        aside={
          <div className="rounded-[var(--radius-card)] bg-surface p-5 sm:p-12">
            <ReportFragment />
          </div>
        }
      />

      {/* ── 계산 방법과 한계 ───────────────────────── */}
      <section
        id="limits"
        aria-labelledby="limits-h"
        className="bg-surface-2 py-32 lg:py-44"
      >
        <div className="frame grid gap-12 lg:grid-cols-[1fr_1.3fr] lg:gap-20">
          <div>
            <h2 id="limits-h" className="title" data-reveal>
              계산 방법과 한계
            </h2>
            <p className="lead mt-6" data-reveal style={i(1)}>
              가게별 월매출은 공개 데이터가 아니어서, 학습용 매출은
              시뮬레이션하고 양 끝을 실제 통계에 맞췄습니다.
            </p>
          </div>
          <dl className="grid gap-8">
            {[
              [
                "정확도 83.8%는 시뮬레이션 규칙 복원율입니다",
                "이 값은 시뮬레이션 규칙을 모델이 되찾은 비율입니다. 실제 가게의 미래를 맞힌 비율이 아닙니다.",
              ],
              [
                "위험 등급의 세 원인은 아직 가려내기 어렵습니다",
                "매출 폭락·고금리 과다채무·상권 침체는 같은 매출 궤적에서 만들어져, 원인은 확률로만 보여 드립니다.",
              ],
              [
                "사전확률을 서울 실제 값으로 보정합니다",
                "학습 위험군 비중 0.30을 서울 실제 약 0.14로 되돌려 모든 사용자의 위험도가 부풀지 않게 합니다.",
              ],
              [
                "매출 실금액은 저장하지 않습니다",
                "1개월차 = 100인 지수만 남깁니다. 공유 링크에도 매출 관련 수치는 빠집니다.",
              ],
            ].map(([t, d], k) => (
              <div key={t} data-reveal style={i(k)}>
                <dt className="text-xl font-bold">{t}</dt>
                <dd className="mt-2">{d}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* ── 마무리 ─────────────────────────────── */}
      <section
        aria-labelledby="go"
        className="frame flex flex-wrap items-end justify-between gap-8 py-32 lg:py-44"
      >
        <h2 id="go" className="title max-w-[40rem]" data-reveal>
          우리 동네부터 볼까요, 내 가게부터 볼까요
        </h2>
        <div className="flex flex-wrap gap-3" data-reveal style={i(1)}>
          <Link href="/market" className="btn btn-quiet">
            상권 신호등 보기
          </Link>
          <Link href="/diagnosis" className="btn btn-primary">
            내 가게 진단받기 <Arrow />
          </Link>
        </div>
      </section>
    </main>
  );
}

function Chapter({
  id,
  title,
  lead,
  href,
  cta,
  aside,
  flip = false,
  children,
}: {
  id: string;
  title: string;
  lead: string;
  href: string;
  cta: string;
  aside: ReactNode;
  flip?: boolean;
  children?: ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-h`}
      className="frame grid gap-12 py-28 lg:grid-cols-2 lg:items-center lg:gap-24 lg:py-44"
    >
      <div className={flip ? "lg:order-2" : undefined}>
        <h2 id={`${id}-h`} className="title" data-reveal>
          {title}
        </h2>
        <p className="lead mt-6" data-reveal style={i(1)}>
          {lead}
        </p>
        {children && (
          <div data-reveal style={i(2)}>
            {children}
          </div>
        )}
        <Link
          href={href}
          className="btn btn-primary mt-10"
          data-reveal
          style={i(3)}
        >
          {cta} <Arrow />
        </Link>
      </div>
      <div data-reveal style={i(2)}>
        {aside}
      </div>
    </section>
  );
}
