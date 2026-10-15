// POST /api/solutions { riskType, query?, topK? } — F-RAG-03 하이브리드 검색 (목업: 키워드 점수)
import { NextRequest, NextResponse } from 'next/server';
import { retrieve, toSolution } from '@/lib/policies';
import { RISK_TYPES } from '@/lib/risk';
import { store } from '@/lib/store';
import type { RiskType } from '@/lib/types';

export async function POST(req: NextRequest) {
  const { riskType, query = '', topK = 3 } = await req.json();
  if (!RISK_TYPES.includes(riskType)) return NextResponse.json({ error: 'riskType이 올바르지 않습니다.' }, { status: 400 });
  const { docs, fallback } = retrieve(riskType as RiskType, topK, query);
  store.metrics.ragQueries++;
  if (!docs.length) store.metrics.ragEmpty++;
  return NextResponse.json({ riskType, fallback, solutions: docs.map(toSolution) });
}
