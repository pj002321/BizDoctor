import Image from "next/image";
import Link from "next/link";
import CountUp from "@/components/CountUp";
import { Arrow, Check, SignalShape } from "@/components/icons";
import Lamps from "@/components/Lamps";
import data from "./data/seoul.json";
import {
  GradeFragment,
  RankingFragment,
  ReportFragment,
  SolutionsFragment,
} from "./fragments";
import SeoulSignalMap from "./SeoulSignalMap";
import ServiceList, { type ServiceItem } from "./ServiceList";

const i = (n: number) => ({ ["--i" as string]: n });

const SERVICES: ServiceItem[] = [
  {
    title: "상권 신호등",
    body: "25개 자치구에서 행정동 성적표, 업종별 11개 분기 추이까지 지도로 좁혀 봅니다.",
    href: "/market",
    cta: "상권 신호등 보기",
  },
  {
    title: "산업 추이 · 업종 순위",
    body: "어느 업종이 분기마다 얼마나 문을 닫는지, 서울 전체 흐름을 순위로 봅니다.",
    href: "/service#trend",
    cta: "산업 추이 안내",
  },
  {
    title: "사업장 진단 등급",
    body: "최근 3개월 매출과 업종·동네만 넣으면 A·B·C 등급과 추정 원인을 확률로 보여 드립니다.",
    href: "/diagnosis",
    cta: "진단 시작",
  },
  {
    title: "맞춤 지원사업",
    body: "추정 원인에 맞는 2026년 정책자금·채무조정·재기지원 사업을 공고 원문에서 찾습니다.",
    href: "/service#solutions",
    cta: "지원사업 안내",
  },
  {
    title: "AI 리포트 · 상담",
    body: "진단 결과를 쉬운 말로 풀어 쓰고, 이어지는 질문에 진단 기준으로 답합니다.",
    href: "/report",
    cta: "AI 리포트 보기",
  },
];

const SOURCES = [
  ["서울시 상권분석서비스", "점포-행정동 패널, 12개 분기"],
  ["KOSIS 사업체운영 애로사항", "주의 등급의 원인 비중"],
  ["신용보증기금 채권관리", "위험 등급의 실제 부실 사유"],
  ["2026년 지원사업 공고", "정책자금·채무조정·재기지원"],
];

const COUNTS = [
  [data.counts.gu, "개", "서울 자치구"],
  [data.counts.dong, "개", "행정동"],
  [data.counts.service, "개", "서비스 업종"],
  [data.counts.quarters, "분기", "폐업 통계 관측"],
] as const;

export default function LandingPage() {
  return (
    <main>
      {/* ── 히어로: 시장 사진 위에 신호등 ─────────────── */}
      <section className="on-night relative isolate overflow-hidden bg-night text-on-night">
        <Image
          src="/photos/gwangjang-market-seoul-02.jpg"
          alt="손님으로 붐비는 광장시장 먹자골목, 간판이 늘어선 통로"
          fill
          priority
          sizes="100vw"
          className="photo-drift -z-10 object-cover object-[50%_40%]"
        />
        <div className="absolute inset-0 -z-10 bg-[rgb(18_21_19/0.72)]" />

        <div className="frame grid min-h-[min(52rem,calc(100svh-6.75rem))] items-end gap-12 pt-28 pb-16 lg:grid-cols-[1fr_auto] lg:pb-20">
          <div>
            <Lamps className="fade-up" size="1.25rem" />
            <h1 className="display mt-8">
              <span className="rise-line">
                <span style={i(0)}>폐업 신호를,</span>
              </span>
              <span className="rise-line">
                <span style={i(1)}>먼저 읽어 드립니다</span>
              </span>
            </h1>
            <p className="lead fade-up mt-8 max-w-[38rem]" style={i(0)}>
              BizDoctor는 서울 425개 행정동 · 100개 업종의 상권 통계로 우리 동네
              신호등을 보여 주고, 최근 3개월 매출로 내 가게의 진단 등급과 맞는
              2026년 지원사업을 찾아 드립니다.
            </p>
            <div className="fade-up mt-10 flex flex-wrap gap-3" style={i(1)}>
              <Link href="/diagnosis" className="btn btn-primary">
                내 가게 진단받기 <Arrow />
              </Link>
              <Link href="/market" className="btn btn-light">
                상권 신호등 보기
              </Link>
            </div>
            <ul
              className="fade-up mt-10 flex flex-wrap gap-x-6 gap-y-3 text-[0.9375rem] text-on-night-muted"
              style={i(2)}
            >
              <li className="flex items-center gap-2">
                <Check /> 매출 금액은 저장하지 않아요
              </li>
              <li className="flex items-center gap-2">
                <Check /> 원인은 확률과 함께 추정으로
              </li>
              <li className="flex items-center gap-2">
                <Check /> 리포트 수치는 원문과 대조
              </li>
            </ul>
          </div>

          <div
            data-ui
            className="float-card fade-up hidden w-[19rem] justify-self-end rounded-[var(--radius-card)] bg-bg p-6 text-fg sm:block"
            style={i(4)}
          >
            <div className="bob">
              <p className="text-sm text-muted">
                상권 신호등 · 마포구 전체 업종
              </p>
              <div className="mt-4 grid grid-cols-3 gap-3">
                {(["g", "y", "r"] as const).map((s) => (
                  <span key={s}>
                    <span className="flex items-center gap-1.5 text-sm font-semibold">
                      <SignalShape s={s} size={10} />
                      {s === "g" ? "양호" : s === "y" ? "주의" : "위험"}
                    </span>
                    <span className="text-3xl font-bold">
                      <CountUp to={data.stats.마포구.all[s]} />
                    </span>
                  </span>
                ))}
              </div>
              <p className="mt-3 text-sm text-muted">행정동 × 산업 칸 수</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 숫자 띠 ───────────────────────────── */}
      <section aria-labelledby="scale" className="frame py-16 lg:py-20">
        <h2 id="scale" className="sr-only">
          계산에 쓰는 데이터 범위
        </h2>
        <ul className="grid grid-cols-2 gap-x-8 gap-y-12 lg:grid-cols-4">
          {COUNTS.map(([n, unit, label], k) => (
            <li key={label} data-reveal style={i(k)}>
              <p className="text-[clamp(3rem,5.6vw,5rem)] leading-none font-bold tracking-[-0.045em]">
                <CountUp to={n} />
                <span className="ml-1 text-[0.4em] tracking-normal text-muted">
                  {unit}
                </span>
              </p>
              <p className="mt-3 text-lg">{label}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ── 서비스 ─────────────────────────────── */}
      <section aria-labelledby="services" className="bg-surface py-32 lg:py-44">
        <div className="frame">
          <div className="mb-20 grid gap-6 lg:grid-cols-[1fr_1.05fr] lg:items-end lg:gap-24">
            <h2 id="services" className="title" data-reveal>
              상권부터 내 가게, 지원사업까지 한 흐름으로
            </h2>
            <p className="lead max-w-[34rem]" data-reveal style={i(1)}>
              동네가 어떤지 보고, 내 가게를 진단하고, 받을 수 있는 지원을
              찾습니다. 세 결과는 이름과 색 범례를 따로 써서 섞이지 않게
              했습니다.
            </p>
          </div>
          <ServiceList
            items={SERVICES}
            previews={[
              <figure
                key="p0"
                className="relative aspect-[4/3] overflow-hidden rounded-[var(--radius-card)]"
              >
                <Image
                  src="/photos/namdaemun-market-in-seoul-i.jpg"
                  alt="남대문시장 5번 게이트 앞 상점가, 만국기 아래로 지나는 사람들"
                  fill
                  sizes="(min-width: 1024px) 45vw, 100vw"
                  className="object-cover"
                />
              </figure>,
              <RankingFragment key="p1" />,
              <GradeFragment key="p2" />,
              <SolutionsFragment key="p3" />,
              <ReportFragment key="p4" />,
            ]}
          />
        </div>
      </section>

      {/* ── 지도 (직접 눌러 보는 부분) ─────────────── */}
      <section aria-labelledby="map" className="frame py-32 lg:py-44">
        <div className="mb-16 grid gap-6 lg:grid-cols-[1.35fr_1fr] lg:items-end lg:gap-20">
          <h2 id="map" className="title" data-reveal>
            우리 구 상권 신호등, 직접 짚어 보세요
          </h2>
          <p data-reveal style={i(1)}>
            2023 Q1 – 2025 Q3 서울시 상권분석서비스 기준. 관측 8개 분기 · 점포
            100개 미만인 칸은 ‘표본 적음’으로 따로 셉니다.
          </p>
        </div>
        <div data-reveal style={i(2)}>
          <SeoulSignalMap />
        </div>
      </section>

      {/* ── 사진 띠 ─────────────────────────────── */}
      <section
        aria-labelledby="street"
        className="relative h-[70vh] min-h-[28rem] overflow-hidden bg-night"
      >
        <Image
          src="/photos/led-shop-in-euljiro-seoul.jpg"
          alt="을지로 공구·조명 상가 앞 인도에 진열된 물건들"
          fill
          sizes="100vw"
          className="parallax object-cover"
        />
        <div className="absolute inset-0 bg-[rgb(18_21_19/0.6)]" />
        <div className="frame relative flex h-full items-end pb-16">
          <div className="on-night max-w-[44rem] text-on-night">
            <h2 id="street" className="title" data-reveal>
              골목마다 사정이 다릅니다
            </h2>
            <p className="lead mt-6" data-reveal style={i(1)}>
              같은 업종이라도 행정동마다 폐업 흐름이 다릅니다. 그래서 진단은
              언제나 내 가게가 있는 동네의 같은 업종과 견줘서 합니다.
            </p>
          </div>
        </div>
      </section>

      {/* ── 원칙과 범위 ─────────────────────────── */}
      <section aria-labelledby="honest" className="frame py-32 lg:py-44">
        <div className="grid gap-16 lg:grid-cols-[1fr_1fr] lg:items-center lg:gap-24">
          <figure
            className="relative aspect-[4/5] overflow-hidden rounded-[var(--radius-card)] sm:aspect-[4/3] lg:aspect-[4/5]"
            data-reveal
          >
            <Image
              src="/photos/gwangjang-market-seoul-01.jpg"
              alt="종로 광장시장 정문, 줄무늬 외벽과 간판"
              fill
              sizes="(min-width: 1024px) 45vw, 100vw"
              className="object-cover"
            />
          </figure>
          <div>
            <h2 id="honest" className="title" data-reveal>
              추정은 추정이라고 말합니다
            </h2>
            <dl className="mt-14 grid gap-10">
              {[
                [
                  "매출은 지수로만 남깁니다",
                  "입력한 금액은 1개월차 = 100인 지수로 바꿔 계산에만 쓰고, 실제 금액은 저장하지 않습니다.",
                ],
                [
                  "원인 유형은 확률과 함께",
                  "여섯 가지 위기 유형 가운데 일부는 지금 모델로 구분이 어렵습니다. 그래서 ‘추정 원인’과 확률로만 보여 드립니다.",
                ],
                [
                  "서울 실제 비율로 보정합니다",
                  "학습 데이터의 위험군 비중(30%)을 서울 실제 비중(약 14%)으로 되돌려, 위험도가 부풀지 않게 합니다.",
                ],
              ].map(([t, d], k) => (
                <div key={t} data-reveal style={i(k + 1)}>
                  <dt className="text-xl font-bold">{t}</dt>
                  <dd className="mt-2 max-w-[34rem]">{d}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>

      {/* ── 데이터 출처 ───────────────────────── */}
      <section aria-labelledby="sources" className="bg-surface">
        <div className="frame py-16 lg:py-20">
          <h2 id="sources" className="text-xl font-bold">
            네 가지 공개 데이터로 계산합니다
          </h2>
          <ul className="mt-10 grid grid-cols-1 gap-x-12 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
            {SOURCES.map(([name, what], k) => (
              <li key={name} data-reveal style={i(k)}>
                <p className="text-lg font-semibold">{name}</p>
                <p className="mt-1">{what}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── 마무리: 켜지는 신호등 ─────────────────── */}
      <section
        aria-labelledby="start"
        className="on-night bg-night text-on-night"
      >
        <div className="frame grid gap-16 py-32 lg:grid-cols-[1fr_auto] lg:items-center lg:gap-24 lg:py-40">
          <div>
            <h2 id="start" className="title" data-reveal>
              최근 3개월 매출만 있으면 됩니다
            </h2>
            <p className="lead mt-6 max-w-[34rem]" data-reveal style={i(1)}>
              행정동과 업종을 고르고 석 달 치 매출을 넣으면, 진단 등급과 추정
              원인, 맞는 지원사업과 AI 리포트가 한 화면에 나옵니다.
            </p>
            <div
              className="mt-10 flex flex-wrap gap-3"
              data-reveal
              style={i(2)}
            >
              <Link href="/diagnosis" className="btn btn-primary">
                내 가게 진단받기 <Arrow />
              </Link>
              <Link href="/service" className="btn btn-light">
                서비스 자세히 보기
              </Link>
            </div>
          </div>
          <div data-reveal style={i(2)}>
            <Lamps vertical size="clamp(4.5rem, 9vw, 7.5rem)" />
          </div>
        </div>
      </section>
    </main>
  );
}
