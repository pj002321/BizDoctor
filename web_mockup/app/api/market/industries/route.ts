// GET /api/market/industries?sort=avg|real&top=N — F-MAP-05 업종별 폐업률 순위 (관측 200건 이상 100개 업종)
import { NextRequest, NextResponse } from 'next/server';
import { getIndustryRanking } from '@/lib/data';
import type { IndustryRank } from '@/lib/types';

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const key = sp.get('sort') === 'real' ? 'realCloseRate' : 'avgCloseRate';
  const top = Math.min(100, Number(sp.get('top') ?? 100) || 100);
  const ranked: IndustryRank[] = getIndustryRanking()
    .filter((r) => r.obs >= 200)
    .sort((a, b) => b[key] - a[key])
    .slice(0, top)
    .map((r, i) => ({ rank: i + 1, name: r.name, industry: r.industry, avgCloseRate: r.avgCloseRate, realCloseRate: r.realCloseRate, obs: r.obs, stores: r.stores }));
  return NextResponse.json({ sort: key, items: ranked });
}
