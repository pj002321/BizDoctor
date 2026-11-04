"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Arrow } from "./icons";

const NAV = [
  { href: "/market", label: "상권 신호등" },
  { href: "/diagnosis", label: "사업장 진단" },
  { href: "/report", label: "AI 리포트" },
  { href: "/service", label: "서비스 안내" },
] as const;

export default function SiteHeader() {
  const path = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="on-night bg-night text-[0.8125rem] text-on-night-muted">
        <div className="frame flex h-9 items-center justify-between gap-4">
          <p className="truncate">
            서울시 상권분석서비스 2023 Q1 – 2025 Q3 · 425개 행정동 기준
          </p>
          <Link
            href="/service#limits"
            className="link-under hidden shrink-0 text-on-night sm:inline"
          >
            계산 방법과 한계
          </Link>
        </div>
      </div>

      <header className="sticky top-0 z-40 bg-bg">
        <div className="frame flex h-[4.5rem] items-center justify-between gap-6">
          <Link
            href="/"
            className="flex items-center gap-2.5 text-[1.375rem] font-bold tracking-[-0.03em]"
            aria-label="BizDoctor 홈"
            onClick={() => setOpen(false)}
          >
            <Mark />
            BizDoctor
          </Link>

          <nav aria-label="주요 메뉴" className="hidden lg:block">
            <ul className="flex items-center gap-1">
              {NAV.map((n) => {
                const active = path.startsWith(n.href);
                return (
                  <li key={n.href}>
                    <Link
                      href={n.href}
                      aria-current={active ? "page" : undefined}
                      className="relative px-4 py-2 font-medium text-muted transition-colors duration-150 hover:text-fg aria-[current=page]:text-accent"
                    >
                      {n.label}
                      <span
                        aria-hidden="true"
                        className={`absolute inset-x-4 -bottom-[1.3rem] h-[3px] origin-left bg-accent transition-transform duration-300 ease-[var(--ease-out-expo)] ${active ? "scale-x-100" : "scale-x-0"}`}
                      />
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          <div className="flex items-center gap-2">
            <Link
              href="/diagnosis"
              className="btn btn-primary hidden !min-h-11 !px-5 text-[0.9375rem] whitespace-nowrap sm:inline-flex"
            >
              내 가게 진단 <Arrow />
            </Link>
            <button
              type="button"
              className="grid size-11 place-items-center rounded-full bg-surface lg:hidden"
              aria-expanded={open}
              aria-controls="mobile-nav"
              aria-label={open ? "메뉴 닫기" : "메뉴 열기"}
              onClick={() => setOpen((v) => !v)}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                aria-hidden="true"
                className="text-fg"
              >
                <path
                  d={open ? "M4 4l12 12M16 4L4 16" : "M3 6h14M3 10h14M3 14h14"}
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="square"
                />
              </svg>
            </button>
          </div>
        </div>

        <nav
          id="mobile-nav"
          aria-label="주요 메뉴"
          hidden={!open}
          className="bg-bg pb-4 lg:hidden"
        >
          <ul className="frame grid">
            {NAV.map((n) => (
              <li key={n.href}>
                <Link
                  href={n.href}
                  onClick={() => setOpen(false)}
                  aria-current={path.startsWith(n.href) ? "page" : undefined}
                  className="block py-3 text-lg font-semibold aria-[current=page]:text-accent"
                >
                  {n.label}
                </Link>
              </li>
            ))}
            <li className="pt-2">
              <Link
                href="/diagnosis"
                onClick={() => setOpen(false)}
                className="btn btn-primary w-full justify-center"
              >
                내 가게 진단 <Arrow />
              </Link>
            </li>
          </ul>
        </nav>
      </header>
    </>
  );
}

/** 신호등 세 칸을 세로로 세운 표지. */
function Mark() {
  return (
    <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
      <rect width="30" height="30" rx="9" fill="var(--color-night)" />
      <circle cx="15" cy="7.8" r="3.3" fill="var(--color-lamp-red)" />
      <circle cx="15" cy="15" r="3.3" fill="var(--color-lamp-yellow)" />
      <circle cx="15" cy="22.2" r="3.3" fill="var(--color-lamp-green)" />
    </svg>
  );
}
