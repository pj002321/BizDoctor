import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "상권 신호등", template: "%s · 상권 신호등" },
  description:
    "서울 상권 통계로 소상공인 경영 위기를 진단하고 맞는 지원사업을 찾아 줍니다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko">
      <head>
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
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
