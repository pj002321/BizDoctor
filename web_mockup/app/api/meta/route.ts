// GET /api/meta — 폼·필터용 선택지 (자치구, 행정동, 산업대분류, 업종, 분기)
import { NextResponse } from 'next/server';
import { GU_LIST, getDongs, getMeta, getServices } from '@/lib/data';

export async function GET() {
  const services = getServices();
  return NextResponse.json({
    quarters: getMeta().quarters,
    gus: GU_LIST(),
    dongs: getDongs(),
    industries: [...new Set(services.map((s) => s.kosis))].sort(),
    services,
  });
}
