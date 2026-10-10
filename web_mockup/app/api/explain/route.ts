// POST /api/explain { gu, industry?, dongCode?, service? } — F-LLM-04 상권 지표 자연어 해설 (목업: 템플릿, 입력 키 캐싱)
import { NextRequest, NextResponse } from 'next/server';
import { regionRisks, parseFilter, getQuarterly } from '@/lib/data';
import { MARKET_SIGNAL } from '@/lib/risk';

const cache = new Map<string, string>();

export async function POST(req: NextRequest) {
  const { gu, industry } = await req.json();
  const key = `${gu}|${industry ?? ''}`;
  if (cache.has(key)) return NextResponse.json({ text: cache.get(key), cached: true });
  const f = parseFilter(new URLSearchParams(industry ? { industry } : {}));
  const all = regionRisks(f);
  const r = all.find((x) => x.gu === gu);
  if (!r) return NextResponse.json({ error: '자치구를 찾을 수 없습니다.' }, { status: 404 });
  const rank = [...all].sort((a, b) => b.realCloseRate - a.realCloseRate).findIndex((x) => x.gu === gu) + 1;
  const diff = r.realCloseRate - r.avgCloseRate;
  const q = getQuarterly().filter((x) => (industry ? x.industry === industry : true));
  const flip = q.filter((x) => x.quarter === '2024 Q1');
  const flipped = flip.filter((x) => x.avgCloseRate > x.avgOpenRate).length;
  const text =
    `${gu}${industry ? ` ${industry}` : ''}의 실질폐업률은 ${r.realCloseRate.toFixed(2)}%로 서울 25개 자치구 중 ${rank}번째로 높고, ` +
    `상권 신호는 '${MARKET_SIGNAL[r.signal].label}'입니다. 단순 평균폐업률(${r.avgCloseRate.toFixed(2)}%)과 ${Math.abs(diff).toFixed(2)}%p 차이가 나는데, ` +
    `${diff < 0 ? '점포 수가 적은 셀의 높은 폐업률이 평균을 끌어올렸기 때문' : '점포 수가 많은 셀에서 폐업이 더 많이 발생했기 때문'}입니다. ` +
    `2024년 1분기에는 ${flip.length}개 산업 중 ${flipped}개에서 폐업률이 개업률을 넘어서는 역전이 나타났습니다.`;
  cache.set(key, text);
  return NextResponse.json({ text, cached: false });
}
