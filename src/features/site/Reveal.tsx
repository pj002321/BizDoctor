"use client";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

/** [data-reveal] 요소가 화면에 들어오면 is-in 을 붙인다. 한 번만. 페이지 이동마다 다시 건다. */
export default function Reveal() {
  const path = usePathname();
  useEffect(() => {
    void path;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (!e.isIntersecting) continue;
          e.target.classList.add("is-in");
          io.unobserve(e.target);
        }
      },
      { rootMargin: "0px 0px -10% 0px" },
    );
    for (const el of document.querySelectorAll("[data-reveal]:not(.is-in)"))
      io.observe(el);
    return () => io.disconnect();
  }, [path]);
  return null;
}
