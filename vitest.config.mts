import { defineConfig } from "vitest/config";

// 테스트는 features/*/domain 순수 함수에만 쓴다(AGENTS.md). 그래서 jsdom 없이 node 환경.
export default defineConfig({
  resolve: { tsconfigPaths: true },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
