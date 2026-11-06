import "server-only";
import fs from "node:fs";
import path from "node:path";
import index from "./index.json";

/**
 * 목업 데이터 읽기. 실서비스에서는 이 파일 자리에서 Postgres(region_risk · panel_cell)를 읽는다(F-SYS-03).
 * 행 모양: ind[k] = [신호, 위험가중치, 평균폐업률, 관측분기] | ["low", 관측분기] | null
 *          series[행정동][업종] = 분기별 [점포수, 폐업률, 개업률, percentile] | null
 */
export type Sig = "g" | "y" | "r";
export type IndCell = [Sig, number, number, number] | ["low", number] | null;
export type Row = [number, number, number, number | null] | null;
export interface GuData {
  gu: string;
  dongs: { code: string; name: string; ind: IndCell[] }[];
  series: Record<string, Record<string, Row[]>>;
}

export const META = index;
export const GU_LIST = index.map.shapes
  .map((s) => s.gu)
  .sort((a, b) => a.localeCompare(b, "ko"));

export function loadGu(gu: string): GuData | null {
  if (!GU_LIST.includes(gu)) return null;
  const file = path.join(
    process.cwd(),
    "src/features/market/data/gu",
    `${gu}.json`,
  );
  return JSON.parse(fs.readFileSync(file, "utf-8"));
}
