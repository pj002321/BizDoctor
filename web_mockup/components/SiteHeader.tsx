'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV = [
  { href: '/market', label: '상권 신호등' },
  { href: '/market/trends', label: '산업 추이' },
  { href: '/market/industries', label: '업종 순위' },
  { sep: true },
  { href: '/diagnosis', label: '사업장 진단' },
  { href: '/methodology', label: '계산 방법' },
  { sep: true },
  { href: '/chatbot', label: '챗봇 상담' },
] as const;

export default function SiteHeader() {
  const path = usePathname();
  const active = (href: string) => (href === '/market' ? path === '/market' : path.startsWith(href));
  return (
    <header className="site-header">
      <div className="container bar">
        {/* 랜딩(public/landing.html)은 Next 페이지가 아니라서 Link 대신 a 태그로 이동 */}
        <a href="/" className="brand" aria-label="BizDoctor 홈">
          <span className="brand-mark" aria-hidden>B</span>BizDoctor
        </a>
        <nav className="nav" aria-label="주요 메뉴">
          {NAV.map((n, i) =>
            'sep' in n ? <span key={i} className="sep" aria-hidden /> : (
              <Link key={n.href} href={n.href} aria-current={active(n.href) ? 'page' : undefined}>{n.label}</Link>
            ),
          )}
        </nav>
      </div>
    </header>
  );
}
