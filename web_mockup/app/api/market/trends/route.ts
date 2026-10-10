// GET /api/market/trends?industry=a&industry=b — F-MAP-04 분기별 산업 추이
import { NextRequest, NextResponse } from 'next/server';
import { getQuarterly } from '@/lib/data';
import type { TrendsResponse } from '@/lib/types';

export async function GET(req: NextRequest) {
  const inds = req.nextUrl.searchParams.getAll('industry');
  const rows = getQuarterly().filter((r) => inds.length === 0 || inds.includes(r.industry));
  const body: TrendsResponse = {
    series: rows.map(({ quarter, industry, avgCloseRate, avgOpenRate, realCloseRate }) => ({ quarter, industry, avgCloseRate, avgOpenRate, realCloseRate })),
    annotations: [{ quarter: '2024 Q1', label: '개업률·폐업률 역전' }],
  };
  return NextResponse.json(body);
}
