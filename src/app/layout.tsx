import type { Metadata } from "next";
import Reveal from "@/features/site/Reveal";
import SiteFooter from "@/features/site/SiteFooter";
import SiteHeader from "@/features/site/SiteHeader";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "BizDoctor — 상권 신호등 · 사업장 진단",
    template: "%s · BizDoctor",
  },
  description:
    "서울 상권 통계로 소상공인 경영 위기를 진단하고 맞는 지원사업을 찾아 줍니다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        {/* 스크립트가 돌 때만 등장 모션을 켠다. 안 돌면 내용이 그대로 보인다. */}
        <script
          // biome-ignore lint/security/noDangerouslySetInnerHtml: 고정 문자열 한 줄, 사용자 입력 없음
          dangerouslySetInnerHTML={{
            __html: 'document.documentElement.classList.add("js")',
          }}
        />
        {/* 한글 본문 폰트. CDN 이 죽어도 globals.css 의 --font-sans 가 시스템 폰트로 폴백한다. */}
        <link
          rel="preconnect"
          href="https://cdn.jsdelivr.net"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body className="font-sans antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-bg focus:p-3"
        >
          본문 바로가기
        </a>
        <SiteHeader />
        <div id="main">{children}</div>
        <SiteFooter />
        <Reveal />
      </body>
    </html>
  );
}
