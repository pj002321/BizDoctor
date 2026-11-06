// 상권 신호등·사업장 진단 목업 데이터. web_mockup/data(실제 CSV 추출본)에서 뽑는다.
// 재생성: node src/features/market/data/build-market-data.mjs
//
// 신호 기준은 web_mockup/lib/data.ts dongRisks 와 같다:
//   관측 8개 분기 이상 · 점포 합 100 이상인 행정동 × 산업 칸만 판정, 위험가중치(percentile 평균) 0.60 / 0.85.
// ⚠ 원본 행의 점포수는 점포_수(프랜차이즈 제외)다. 유사_업종_점포_수가 들어오기 전까지
//   "표본 적음"(점포 5개 이하) 판정이 프랜차이즈 비중만큼 과하게 붙는다. Postgres 적재 때 바꾼다.
import fs from "node:fs";
import path from "node:path";

const SRC = path.resolve("web_mockup/data");
const load = (f) => JSON.parse(fs.readFileSync(path.join(SRC, f), "utf-8"));
const services = load("service_industries.json");
const kosisOf = new Map(services.map((s) => [s.code, s.kosis]));
const dongs = load("dongs.json");
const geo = load("seoul_gu_paths.json");
const meta = load("meta.json");

const INDUSTRIES = [
  ["숙박 및 음식점업", "음식점"],
  ["도매 및 소매업", "소매"],
  ["교육 서비스업", "교육"],
  ["협회 및 단체, 수리 및 기타 개인서비스업", "개인 서비스"],
  ["예술, 스포츠 및 여가관련 서비스업", "여가"],
  ["부동산업", "부동산"],
  ["전문과학기술서비스업", "전문 서비스"],
  ["사업시설관리, 사업지원 및 임대 서비스업", "사업 지원"],
];
const indIdx = new Map(INDUSTRIES.map(([n], i) => [n, i]));
const signal = (w) => (w > 0.85 ? "r" : w > 0.6 ? "y" : "g");
const r = (v, d = 3) => Math.round(v * 10 ** d) / 10 ** d;

const OUT = path.resolve("src/features/market/data");
fs.mkdirSync(path.join(OUT, "gu"), { recursive: true });
const DIAG = path.resolve("src/features/diagnosis/data");
fs.mkdirSync(DIAG, { recursive: true });

const summary = {};
const latest = {}; // 진단용: 행정동|업종 → 가장 최근 관측 [분기 인덱스, percentile, 폐업·개업 격차, 폐업률]

for (const { gu } of geo.shapes) {
  const cells = load(`cells/${gu}.json`);
  const guDongs = [];
  const series = {};
  const guAcc = INDUSTRIES.map(() => ({ g: 0, y: 0, r: 0, low: 0 }));

  for (const [dong, bySvc] of Object.entries(cells)) {
    const acc = INDUSTRIES.map(() => ({ n: 0, stores: 0, pct: 0, close: 0 }));
    series[dong] = {};
    for (const [svc, rows] of Object.entries(bySvc)) {
      const k = indIdx.get(kosisOf.get(svc));
      series[dong][svc] = rows.map((row) =>
        row ? [row[0], row[3], row[4], row[6]] : null,
      );
      for (let q = rows.length - 1; q >= 0; q--) {
        const row = rows[q];
        if (row && row[6] != null) {
          latest[`${dong}|${svc}`] = [q, row[6], row[5], row[3]];
          break;
        }
      }
      if (k == null) continue;
      for (const row of rows) {
        if (!row || row[0] < 5) continue;
        acc[k].n++;
        acc[k].stores += row[0];
        acc[k].pct += row[6];
        acc[k].close += row[3];
      }
    }
    const ind = acc.map((a, k) => {
      if (a.n === 0) return null;
      if (a.n < 8 || a.stores < 100) {
        guAcc[k].low++;
        return ["low", a.n];
      }
      const w = a.pct / a.n;
      guAcc[k][signal(w)]++;
      return [signal(w), r(w, 2), r(a.close / a.n, 2), a.n];
    });
    guDongs.push({
      code: dong,
      name: dongs.find((d) => d.code === dong)?.name ?? dong,
      ind,
    });
  }
  guDongs.sort((a, b) => a.name.localeCompare(b.name, "ko"));
  fs.writeFileSync(
    path.join(OUT, "gu", `${gu}.json`),
    JSON.stringify({ gu, dongs: guDongs, series }),
  );
  summary[gu] = guAcc;
}

fs.writeFileSync(
  path.join(OUT, "index.json"),
  JSON.stringify({
    quarters: meta.quarters,
    industries: INDUSTRIES.map(([name, label]) => ({ name, label })),
    services: services.map((s) => ({
      code: s.code,
      name: s.name,
      ind: indIdx.get(s.kosis) ?? null,
    })),
    map: {
      width: geo.width,
      height: geo.height,
      shapes: geo.shapes.map(({ gu, d, cx, cy }) => ({ gu, d, cx, cy })),
    },
    summary,
  }),
);

// 진단 폼 선택지(클라이언트)와 셀 최신값(서버 전용)을 나눠 쓴다.
fs.writeFileSync(
  path.join(DIAG, "catalog.json"),
  JSON.stringify({
    dongs: dongs.map((d) => ({ code: d.code, name: d.name, gu: d.gu })),
    services: services.map((s) => ({
      code: s.code,
      name: s.name,
      kosis: s.kosis,
    })),
    quarters: meta.quarters,
  }),
);
fs.writeFileSync(path.join(DIAG, "latest-cells.json"), JSON.stringify(latest));
console.log(
  "ok",
  Object.keys(summary).length,
  "gu,",
  Object.keys(latest).length,
  "cells",
);
