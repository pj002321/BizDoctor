// POST /api/diagnosis — F-DIA-01~06 + F-RAG-04 신호 JSON 반환
import { NextRequest, NextResponse } from 'next/server';
import { diagnose, InputError } from '@/lib/diagnosis';
import { saveDiagnosis } from '@/lib/store';
import type { DiagnosisRequest } from '@/lib/types';

export async function POST(req: NextRequest) {
  let body: DiagnosisRequest;
  try { body = await req.json(); } catch { return NextResponse.json({ error: '요청 형식이 올바르지 않습니다.' }, { status: 400 }); }
  try {
    const result = diagnose(body);
    // 매출 실금액(body.revenue)은 여기서 버려지고, 저장은 정규화 지수만 (F-SYS-05)
    saveDiagnosis(result);
    return NextResponse.json(result);
  } catch (e) {
    if (e instanceof InputError) return NextResponse.json({ error: e.message }, { status: 422 });
    throw e;
  }
}
