// GET /api/diagnosis/context?dongCode=&service= — F-DIA-07 상권 대비 위치
import { NextRequest, NextResponse } from 'next/server';
import { context, InputError } from '@/lib/diagnosis';

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;
  try {
    const { percentile, topPercent, hist, peers, sentence } = context(sp.get('dongCode') ?? '', sp.get('service') ?? '');
    return NextResponse.json({ percentile, topPercent, hist, peers, sentence });
  } catch (e) {
    if (e instanceof InputError) return NextResponse.json({ error: e.message }, { status: 404 });
    throw e;
  }
}
