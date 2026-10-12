// GET /api/market/regions — F-MAP-01 자치구 위험도 (F-MAP-06 공통 필터 적용)
import { NextRequest, NextResponse } from 'next/server';
import { parseFilter, regionRisks } from '@/lib/data';
import { MAP_THRESHOLDS } from '@/lib/risk';
import type { RegionsResponse } from '@/lib/types';

export async function GET(req: NextRequest) {
  const filter = parseFilter(req.nextUrl.searchParams);
  const body: RegionsResponse = { filter, thresholds: MAP_THRESHOLDS, regions: regionRisks(filter) };
  return NextResponse.json(body);
}
