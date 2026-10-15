// GET /api/market/regions/{gu}/dongs — F-MAP-02 행정동 드릴다운
import { NextRequest, NextResponse } from 'next/server';
import { GU_LIST, dongRisks, parseFilter } from '@/lib/data';
import type { DongsResponse } from '@/lib/types';

export async function GET(req: NextRequest, { params }: { params: Promise<{ gu: string }> }) {
  const gu = decodeURIComponent((await params).gu);
  if (!GU_LIST().includes(gu)) return NextResponse.json({ error: `알 수 없는 자치구: ${gu}` }, { status: 404 });
  const filter = parseFilter(req.nextUrl.searchParams);
  const body: DongsResponse = { gu, filter, dongs: dongRisks(gu, filter) };
  return NextResponse.json(body);
}
