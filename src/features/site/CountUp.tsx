"use client";
import { useEffect, useRef, useState } from "react";

/**
 * 화면에 들어오면 0에서 목표값까지 올라간다. 목표값이 바뀌면 지금 값에서 새 값으로 간다.
 * 서버 렌더와 스크립트가 없는 환경에서는 처음부터 최종값을 보여 준다.
 */
export default function CountUp({
  to,
  decimals = 0,
  duration = 1400,
}: {
  to: number;
  decimals?: number;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [value, setValue] = useState(to);
  const shown = useRef(to);
  const seen = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      shown.current = to;
      setValue(to);
      return;
    }
    let raf = 0;
    const run = (from: number) => {
      const t0 = performance.now();
      const step = (now: number) => {
        const p = Math.min(1, (now - t0) / duration);
        const eased = 1 - 2 ** (-10 * p); // ease-out-expo
        const v = from + (to - from) * (p === 1 ? 1 : eased);
        shown.current = v;
        setValue(v);
        if (p < 1) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    };

    if (seen.current) {
      run(shown.current);
      return () => cancelAnimationFrame(raf);
    }
    // 처음: 0 으로 내려 두고 화면에 들어오면 센다
    shown.current = 0;
    setValue(0);
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        seen.current = true;
        io.disconnect();
        run(0);
      },
      { rootMargin: "0px 0px -10% 0px" },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [to, duration]);

  return (
    <span ref={ref} className="tabular-nums">
      {value.toFixed(decimals)}
    </span>
  );
}
