// GET /api/diagnosis/{id}?token= — F-DIA-08 재조회 / 공유 링크
// token 으로 열람하면 매출 관련 수치(revenueIndex, score, context, features)는 제외
import { NextRequest, NextResponse } from 'next/server';
import { getDiagnosis, store } from '@/lib/store';
import type { SharedDiagnosis } from '@/lib/types';

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const token = req.nextUrl.searchParams.get('token');
  // 공유 토큰으로 조회
  if (token) {
    const d = [...store.diagnoses.values()].find((x) => x.shareToken === token);
    if (!d || !getDiagnosis(d.diagnosisId)) return NextResponse.json({ error: '만료되었거나 존재하지 않는 링크입니다.' }, { status: 404 });
    const shared: SharedDiagnosis = {
      shared: true, diagnosisId: d.diagnosisId, createdAt: d.createdAt, expiresAt: d.expiresAt, input: d.input,
      riskLevel: d.riskLevel, riskType: d.riskType, typeProbs: d.typeProbs, levelProbs: d.levelProbs, solutions: d.solutions,
    };
    return NextResponse.json(shared);
  }
  const d = getDiagnosis(id);
  if (!d) return NextResponse.json({ error: '진단 결과가 없거나 만료되었습니다. (목업: 개발 서버 재시작 시 초기화)' }, { status: 404 });
  return NextResponse.json(d);
}
