import Link from "next/link";
import credits from "./data/photo-credits.json";

export default function SiteFooter() {
  return (
    <footer className="on-navy bg-navy text-on-navy-muted">
      <div className="frame pt-20 pb-10">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <p className="max-w-md text-on-navy">
              서울시 상권 통계로 소상공인의 경영 위기를 미리 읽고, 맞는 2026년
              정부 지원사업을 찾아 드립니다.
            </p>
            <p className="mt-4 max-w-md text-sm">
              진단 결과는 통계 모델의 추정이며, 대출·지원 대상 여부를 확정하지
              않습니다.
            </p>
          </div>
          <nav aria-label="서비스">
            <h2 className="font-semibold text-on-navy">서비스</h2>
            <ul className="mt-4 grid gap-2">
              <li>
                <Link className="link-under" href="/market">
                  상권 신호등
                </Link>
              </li>
              <li>
                <Link className="link-under" href="/diagnosis">
                  사업장 진단
                </Link>
              </li>
              <li>
                <Link className="link-under" href="/report">
                  AI 리포트
                </Link>
              </li>
              <li>
                <Link className="link-under" href="/service">
                  서비스 안내
                </Link>
              </li>
            </ul>
          </nav>
          <div>
            <h2 className="font-semibold text-on-navy">데이터 출처</h2>
            <ul className="mt-4 grid gap-2 text-sm">
              <li>서울시 상권분석서비스 (점포-행정동, 2023–2025)</li>
              <li>KOSIS 사업체운영 애로사항</li>
              <li>신용보증기금 채권관리 부실사유</li>
              <li>2026년 소상공인·중소기업 지원사업 공고</li>
            </ul>
          </div>
        </div>

        <p
          aria-hidden="true"
          className="mt-20 text-[clamp(4rem,17.5vw,15.5rem)] leading-[0.8] font-bold tracking-[-0.055em] text-on-navy"
        >
          BizDoctor
        </p>

        <div className="mt-10 grid gap-2 text-[0.8125rem] leading-relaxed">
          <p>사진</p>
          <ul className="grid gap-1">
            {credits.map((c) => (
              <li key={c.ref}>
                <a className="link-under" href={c.page}>
                  {c.title}
                </a>{" "}
                · {c.creator} · {c.license} · {c.via}
              </li>
            ))}
          </ul>
          <p className="mt-4">© 2026 BizDoctor · 상권 신호등 프로젝트</p>
        </div>
      </div>
    </footer>
  );
}
