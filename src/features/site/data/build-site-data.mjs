// 랜딩·서비스 페이지용 정적 데이터. web_mockup/data(실제 CSV 추출본)에서 한 번 뽑는다.
// 재생성: node src/features/site/data/build-site-data.mjs
// 셀 신호 기준은 web_mockup/lib/data.ts dongRisks 와 같다(관측 8건·점포 100 이상, 위험가중치 0.60/0.85).
// ⚠ 원본 행의 점포수는 점포_수(프랜차이즈 제외)라 여기서 폐업률을 나눠 계산하지 않는다.
import fs from "node:fs";
import path from "node:path";

const SRC = path.resolve("web_mockup/data");
const load = (f) => JSON.parse(fs.readFileSync(path.join(SRC, f), "utf-8"));
const services = new Map(
  load("service_industries.json").map((s) => [s.code, s.kosis]),
);
const dongName = new Map(load("dongs.json").map((d) => [d.code, d.name]));
const geo = load("seoul_gu_paths.json");
const meta = load("meta.json");

const INDUSTRIES = [
  ["숙박 및 음식점업", "음식점"],
  ["도매 및 소매업", "소매"],
  ["교육 서비스업", "교육"],
  ["협회 및 단체, 수리 및 기타 개인 서비스업", "개인 서비스"],
  ["예술, 스포츠 및 여가관련 서비스업", "여가"],
];
const signal = (w) => (w > 0.85 ? "r" : w > 0.6 ? "y" : "g");

const stats = {};
for (const { gu } of geo.shapes) {
  const cells = load(`cells/${gu}.json`);
  const groups = new Map();
  for (const [dong, bySvc] of Object.entries(cells))
    for (const [svc, series] of Object.entries(bySvc)) {
      const ind = services.get(svc);
      const key = `${dong}|${ind}`;
      const g = groups.get(key) ?? { dong, ind, n: 0, stores: 0, pct: 0 };
      for (const row of series) {
        if (!row || row[0] < 5) continue;
        g.n++;
        g.stores += row[0];
        g.pct += row[6];
      }
      groups.set(key, g);
    }
  const byInd = {};
  const bump = (k, g) => {
    byInd[k] ??= { g: 0, y: 0, r: 0, low: 0, watch: [] };
    const s = byInd[k];
    if (g.n < 8 || g.stores < 100) return void s.low++;
    const w = g.pct / g.n;
    s[signal(w)]++;
    if (w > 0.6)
      s.watch.push([
        dongName.get(g.dong) ?? g.dong,
        Math.round(w * 100) / 100,
        k === "all" ? g.ind : null,
      ]);
  };
  for (const g of groups.values()) {
    bump("all", g);
    const i = INDUSTRIES.findIndex(([n]) => n === g.ind);
    if (i >= 0) bump(String(i), g);
  }
  for (const s of Object.values(byInd))
    s.watch = s.watch.sort((a, b) => b[1] - a[1]).slice(0, 3);
  stats[gu] = byInd;
}

const quarterly = load("quarterly.json");
const trend = INDUSTRIES.slice(0, 2).map(([n, label]) => ({
  label,
  values: meta.quarters.map(
    (q) =>
      quarterly.find((r) => r.quarter === q && r.industry === n)
        ?.avgCloseRate ?? null,
  ),
}));
const ranking = load("industry_ranking.json")
  .filter((r) => r.obs >= 1000)
  .sort((a, b) => b.avgCloseRate - a.avgCloseRate)
  .slice(0, 8)
  .map((r) => ({ name: r.name, rate: Math.round(r.avgCloseRate * 100) / 100 }));

const out = {
  quarters: meta.quarters,
  industries: INDUSTRIES.map(([, l]) => l),
  map: {
    width: geo.width,
    height: geo.height,
    shapes: geo.shapes.map(({ gu, d, cx, cy }) => ({ gu, d, cx, cy })),
  },
  stats,
  trend,
  ranking,
  counts: {
    gu: geo.shapes.length,
    dong: dongName.size,
    service: services.size,
    quarters: meta.quarters.length,
  },
};
fs.writeFileSync(
  path.resolve("src/features/site/data/seoul.json"),
  JSON.stringify(out),
);
console.log(
  "ok",
  out.counts,
  JSON.stringify(stats["마포구"].all),
  JSON.stringify(trend),
  JSON.stringify(ranking),
);
