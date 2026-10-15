import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  // 컨테이너용 최소 번들. ⚠️ standalone 은 `.next/static` 과 `public/` 을 복사해 주지
  // 않는다 — Dockerfile 에서 따로 COPY 하지 않으면 CSS·JS 가 전부 404 가 난다.
  output: "standalone",
};

export default nextConfig;
