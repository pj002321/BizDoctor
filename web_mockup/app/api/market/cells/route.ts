// GET /api/market/cells?dongCode=&service= — F-MAP-03 행정동×업종 상세
// service 생략 시 해당 행정동의 업종 목록만 반환
import { NextRequest, NextResponse } from 'next/server';
import { cellSeries, dongByCode, serviceByCode, servicesInDong } from '@/lib/data';
import type { CellResponse } from '@/lib/types';

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  const dongCode = sp.get('dongCode') ?? '';
  const service = sp.get('service');
  const d = dongByCode(dongCode);
  if (!d) return NextResponse.json({ error: 'dongCode가 올바르지 않습니다.' }, { status: 400 });
  if (!service) return NextResponse.json({ dongCode, dong: d.name, gu: d.gu, services: servicesInDong(dongCode) });
  const s = serviceByCode(service);
  const series = cellSeries(dongCode, service);
  if (!s || !series) return NextResponse.json({ error: '해당 조합의 데이터가 없습니다.' }, { status: 404 });
  const body: CellResponse = { dongCode, dong: d.name, gu: d.gu, service, serviceName: s.name, industry: s.kosis, series };
  return NextResponse.json(body);
}
