"use client";
import Link from "next/link";
import { type ReactNode, useState } from "react";
import { Arrow } from "./icons";

export type ServiceItem = {
  title: string;
  body: string;
  href: string;
  cta: string;
};

/** 왼쪽 목록에 마우스·포커스가 가면 오른쪽 화면 조각이 바뀐다. */
export default function ServiceList({
  items,
  previews,
}: {
  items: ServiceItem[];
  previews: ReactNode[];
}) {
  const [on, setOn] = useState(0);
  return (
    <div className="grid gap-10 lg:grid-cols-[1fr_1.05fr] lg:gap-24">
      <ul className="grid content-start">
        {items.map((it, i) => {
          const active = on === i;
          return (
            <li key={it.title} data-reveal style={{ ["--i" as string]: i }}>
              <Link
                href={it.href}
                onMouseEnter={() => setOn(i)}
                onFocus={() => setOn(i)}
                className={`group grid grid-cols-[1fr_auto] items-center gap-x-6 py-8 transition-[padding,background-color] duration-300 ease-[var(--ease-out-expo)] ${active ? "rounded-[var(--radius-card)] bg-bg px-6" : "px-0"}`}
              >
                <span>
                  <span className="block text-[1.625rem] font-bold tracking-[-0.03em]">
                    {it.title}
                  </span>
                  <span className="mt-1 block max-w-[34rem] text-muted">
                    {it.body}
                  </span>
                </span>
                <span
                  className={`grid size-11 place-items-center rounded-full transition-colors duration-300 ${active ? "bg-accent text-white" : "bg-bg text-fg"}`}
                >
                  <Arrow />
                  <span className="sr-only">{it.cta}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="relative rounded-[var(--radius-card)] bg-night p-5 sm:p-12 lg:sticky lg:min-h-[28rem] lg:top-28 lg:self-start">
        <div key={on} className="fade-up" style={{ ["--i" as string]: -4 }}>
          {previews[on]}
        </div>
      </div>
    </div>
  );
}
