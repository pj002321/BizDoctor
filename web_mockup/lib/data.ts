/**
 * 서버 전용 데이터 로더 (목업용).
 * data/*.json 은 실제 CSV 산출물에서 scripts/build_data.py 로 추출한 값.
 * 실제 백엔드에서는 이 역할을 Postgres 사전집계 테이블이 대신함 (F-SYS-02, F-SYS-03).
 */
import fs from 'node:fs';
import path from 'node:path';
import { MAP_THRESHOLDS, signalOf } from './risk';
import type { CellPoint, DongRisk, MarketFilter, RegionRisk } from './types';

const DATA_DIR = path.join(process.cwd(), 'data');
const cache = new Map<string, unknown>();
function load<T>(rel: string): T {
  if (!cache.has(rel)) cache.set(rel, JSON.parse(fs.readFileSync(path.join(DATA_DIR, rel), 'utf-8')));
  return cache.get(rel) as T;
}

export interface Meta { quarters: string[]; latestQuarter: string }
export interface DongInfo { code: string; name: string; gu: string }
export interface ServiceInfo { code: string; name: string; kosis: string }
/** [점포수, 폐업점포수, 개업점포수, 폐업률, 개업률, 폐업개업격차, percentile, 프랜차이즈비중] */
export type CellRow = [number, number, number, number, number, number, number, number | null] | null;
type GuCells = Record<string, Record<string, CellRow[]>>;

export const getMeta = () => load<Meta>('meta.json');
export const getDongs = () => load<DongInfo[]>('dongs.json');
export const getServices = () => load<ServiceInfo[]>('service_industries.json');
export const getGuPaths = () => load<{ width: number; height: number; shapes: { gu: string; eng: string; d: string; cx: number; cy: number }[] }>('seoul_gu_paths.json');
export const getQuarterly = () => load<{ quarter: string; industry: string; stores: number; closed: number; avgCloseRate: number; avgOpenRate: number; realCloseRate: number }[]>('quarterly.json');
export const getIndustryRanking = () => load<{ name: string; industry: string; stores: number; closed: number; avgCloseRate: number; obs: number; realCloseRate: number }[]>('industry_ranking.json');
export const getIndustryDist = () => load<Record<string, { n: number; hist: number[]; meanCloseRate: number }>>('industry_latest_dist.json');
export const GU_LIST = () => [...new Set(getDongs().map((d) => d.gu))].sort((a, b) => a.localeCompare(b, 'ko'));
export const getGuCells = (gu: string) => load<GuCells>(`cells/${gu}.json`);

export function dongByCode(code: string) { return getDongs().find((d) => d.code === code); }
export function serviceByCode(code: string) { return getServices().find((s) => s.code === code); }

/** 쿼리스트링 → 필터 (F-MAP-06) */
export function parseFilter(sp: URLSearchParams): MarketFilter {
  const q = getMeta().quarters;
  const minStores = sp.get('minStores');
  return {
    qFrom: sp.get('qFrom') || q[0],
    qTo: sp.get('qTo') || q[q.length - 1],
    gu: sp.get('gu') || undefined,
    industry: sp.get('industry') || undefined,
    service: sp.get('service') || undefined,
    minStores: minStores == null || minStores === '' ? 5 : Math.max(0, Number(minStores)),
  };
}

function quarterRange(f: MarketFilter): [number, number] {
  const q = getMeta().quarters;
  const a = Math.max(0, q.indexOf(f.qFrom!));
  const b = q.indexOf(f.qTo!);
  return [a, b < 0 ? q.length - 1 : b];
}

interface Acc { stores: number; closed: number; sumClose: number; sumOpen: number; sumPct: number; sumGap: number; n: number }
const newAcc = (): Acc => ({ stores: 0, closed: 0, sumClose: 0, sumOpen: 0, sumPct: 0, sumGap: 0, n: 0 });

/** 셀 단위 순회 — 필터 조건(기간·산업·업종·최소 점포수)을 만족하는 (행정동×업종×분기) 행만 누적 */
function forEachRow(gu: string, f: MarketFilter, fn: (dongCode: string, row: NonNullable<CellRow>) => void) {
  const svc = new Map(getServices().map((s) => [s.code, s.kosis]));
  const [a, b] = quarterRange(f);
  const cells = getGuCells(gu);
  for (const [dongCode, bySvc] of Object.entries(cells)) {
    for (const [svcCode, series] of Object.entries(bySvc)) {
      if (f.service && svcCode !== f.service) continue;
      if (f.industry && svc.get(svcCode) !== f.industry) continue;
      for (let i = a; i <= b; i++) {
        const row = series[i];
        if (!row) continue;
        if (row[0] < (f.minStores ?? 0)) continue;
        fn(dongCode, row);
      }
    }
  }
}
function add(acc: Acc, row: NonNullable<CellRow>) {
  acc.stores += row[0]; acc.closed += row[1]; acc.sumClose += row[3]; acc.sumOpen += row[4]; acc.sumGap += row[5]; acc.sumPct += row[6]; acc.n++;
}
const r2 = (v: number, d = 2) => Math.round(v * 10 ** d) / 10 ** d;

/** F-MAP-01: 자치구 위험도 — 원본 tableau_region_summary.csv 와 동일 산식 (minStores=0, 전체 기간일 때 값 일치) */
export function regionRisks(f: MarketFilter): RegionRisk[] {
  return GU_LIST().map((gu) => {
    const acc = newAcc();
    forEachRow(gu, f, (_d, row) => add(acc, row));
    const w = acc.n ? acc.sumPct / acc.n : 0;
    return {
      gu, signal: signalOf(w), riskWeight: r2(w, 4),
      realCloseRate: acc.stores ? r2((acc.closed / acc.stores) * 100, 3) : 0,
      avgCloseRate: acc.n ? r2(acc.sumClose / acc.n, 3) : 0,
      avgOpenRate: acc.n ? r2(acc.sumOpen / acc.n, 3) : 0,
      stores: acc.stores, obs: acc.n,
    };
  });
}

/** F-MAP-02: 행정동 × 산업 — 관측 8건 이상·연점포수 100 이상만 값 표기, 미달은 '표본부족' */
export function dongRisks(gu: string, f: MarketFilter): DongRisk[] {
  const svc = new Map(getServices().map((s) => [s.code, s.kosis]));
  const names = new Map(getDongs().map((d) => [d.code, d.name]));
  const [a, b] = quarterRange(f);
  const groups = new Map<string, Acc & { dongCode: string; industry: string }>();
  const cells = getGuCells(gu);
  for (const [dongCode, bySvc] of Object.entries(cells)) {
    for (const [svcCode, series] of Object.entries(bySvc)) {
      const ind = svc.get(svcCode)!;
      if (f.industry && ind !== f.industry) continue;
      if (f.service && svcCode !== f.service) continue;
      const key = `${dongCode}|${ind}`;
      if (!groups.has(key)) groups.set(key, { ...newAcc(), dongCode, industry: ind });
      const g = groups.get(key)!;
      for (let i = a; i <= b; i++) {
        const row = series[i];
        if (!row || row[0] < (f.minStores ?? 0)) continue;
        add(g, row);
      }
    }
  }
  return [...groups.values()].map((g) => {
    const ok = g.n >= 8 && g.stores >= 100;
    const w = g.n ? g.sumPct / g.n : null;
    return {
      dongCode: g.dongCode, dong: names.get(g.dongCode) ?? g.dongCode, industry: g.industry,
      sufficient: ok,
      signal: ok && w != null ? signalOf(w, MAP_THRESHOLDS) : null,
      riskWeight: ok && w != null ? r2(w, 4) : null,
      avgCloseRate: ok ? r2(g.sumClose / g.n) : null,
      closeOpenGap: ok ? r2(g.sumGap / g.n) : null,
      obsQuarters: g.n, storeYears: g.stores,
    };
  });
}

/** F-MAP-03: 행정동 × 업종 11개 분기 시계열 */
export function cellSeries(dongCode: string, service: string): CellPoint[] | null {
  const d = dongByCode(dongCode);
  if (!d) return null;
  const series = getGuCells(d.gu)[dongCode]?.[service];
  if (!series) return null;
  return getMeta().quarters.map((quarter, i) => {
    const r = series[i];
    return r
      ? { quarter, stores: r[0], closeRate: r[3], openRate: r[4], closeOpenGap: r[5], percentile: r[6], franchiseShare: r[7], smallSample: r[0] <= 5 }
      : { quarter, stores: null, closeRate: null, openRate: null, closeOpenGap: null, percentile: null, franchiseShare: null, smallSample: true };
  });
}

/** 해당 행정동에 존재하는 업종 목록 (진단 폼·상세 카드 선택지) */
export function servicesInDong(dongCode: string) {
  const d = dongByCode(dongCode);
  if (!d) return [];
  const bySvc = getGuCells(d.gu)[dongCode] ?? {};
  const svc = new Map(getServices().map((s) => [s.code, s]));
  return Object.keys(bySvc).map((c) => svc.get(c)!).filter(Boolean).sort((a, b) => a.name.localeCompare(b.name, 'ko'));
}
