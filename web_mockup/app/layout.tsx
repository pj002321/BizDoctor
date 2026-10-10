import type { Metadata, Viewport } from 'next';
import SiteHeader from '@/components/SiteHeader';
import './globals.css';

export const metadata: Metadata = {
  title: 'BizDoctor — 상권 신호등 · 사업장 진단',
  description: '서울 상권 폐업 위험 지도와 소상공인 사업장 진단, 정책자금 추천 (로컬 목업)',
};
export const viewport: Viewport = { width: 'device-width', initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <a href="#main" className="sr-only">본문 바로가기</a>
        <SiteHeader />
        <main id="main" className="container">{children}</main>
        <footer className="container footer">
          BizDoctor 로컬 목업 · 상권 데이터: 서울시 상권분석서비스(2023 Q1~2025 Q3) 산출물 일부 추출 · 진단·리포트는 목업 로직(실제 모델/LLM 미연결)
        </footer>
      </body>
    </html>
  );
}
