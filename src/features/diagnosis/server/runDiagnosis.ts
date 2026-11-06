"use server";
import "server-only";
import type { Signal } from "@/shared/types/signal";
import catalog from "../data/catalog.json";
import latest from "../data/latest-cells.json";
import {
  causeProbs,
  estimateRawProbs,
  pickCause,
  pickLevel,
  priorCorrect,
  riskScore,
  toSalesIndex,
} from "../domain/diagnose";
import { findSolutions } from "./policies";

/**
 * 사업장 진단(목업). 실서비스에서는 aiFetch("/api/diagnosis") 결과를 그대로 돌려준다.
 * 매출 금액은 이 함수 안에서 지수로 바뀐 뒤 버려진다 — 로그·DB 어디에도 남기지 않는다(F-SYS-05).
 */
export async function runDiagnosis(input: {
  dongCode: string;
  serviceCode: string;
  sales: number[];
}): Promise<{ ok: true; signal: Signal } | { ok: false; error: string }> {
  const dong = catalog.dongs.find((d) => d.code === input.dongCode);
  const service = catalog.services.find((s) => s.code === input.serviceCode);
  if (!dong) return { ok: false, error: "행정동을 골라 주세요." };
  if (!service) return { ok: false, error: "업종을 골라 주세요." };

  let index: [number, number, number];
  try {
    index = toSalesIndex(input.sales);
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }

  const cell = (
    latest as unknown as Record<string, [number, number, number, number]>
  )[`${dong.code}|${service.code}`];
  if (!cell)
    return {
      ok: false,
      error: `${dong.name}에는 ${service.name} 업종 통계가 없습니다. 가까운 업종이나 이웃 행정동으로 골라 주세요.`,
    };
  const [q, percentile, gap, closeRate] = cell;

  const levels = priorCorrect(estimateRawProbs(index, percentile));
  const level = pickLevel(levels);
  const types = causeProbs(levels, index, gap);
  const cause = pickCause(level, types);

  return {
    ok: true,
    signal: {
      risk_level: level,
      risk_type: cause.type,
      risk_type_confidence: cause.confidence,
      score: riskScore(index, levels),
      visual_theme:
        level === "RED" ? "red" : level === "YELLOW" ? "yellow" : "green",
      solutions: findSolutions(cause.type),
      level_probs: levels,
      type_probs: types,
      low_confidence: level === "YELLOW" || cause.confidence < 0.5,
      sales_index: index,
      place: {
        gu: dong.gu,
        dong: dong.name,
        service: service.name,
        industry: service.kosis || "전산업",
      },
      percentile,
      close_rate: closeRate,
      as_of: catalog.quarters[q],
    },
  };
}
