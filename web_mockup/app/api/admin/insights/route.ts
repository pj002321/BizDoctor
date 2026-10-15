// POST /api/admin/insights — 관리자 고객 분석 AI (목업: 진단 기록 집계 + 템플릿 답변)
import { NextRequest, NextResponse } from 'next/server';
import { DIAG_GRADE, RISK_TYPES, RISK_TYPE_META } from '@/lib/risk';
import { store } from '@/lib/store';
import type { InsightRequest, InsightResponse, Signal } from '@/lib/types';

function top<T extends string>(values: T[], n = 3) {
  const count = new Map<T, number>();
  values.forEach((v) => count.set(v, (count.get(v) ?? 0) + 1));
  return [...count.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
}

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as Partial<InsightRequest>;
  const question = String(body.question ?? '').trim();
  if (!question) return NextResponse.json({ error: '질문을 입력해 주세요.' }, { status: 400 });

  const all = [...store.diagnoses.values()];
  const levelFilter: Signal | null = /RED|C등급|위험/.test(question) ? 'RED' : /YELLOW|B등급|주의/.test(question) ? 'YELLOW' : null;
  const rows = levelFilter ? all.filter((d) => d.riskLevel === levelFilter) : all;

  const stats: InsightResponse['stats'] = {
    total: rows.length,
    byLevel: { GREEN: 0, YELLOW: 0, RED: 0 },
    byRiskType: RISK_TYPES.map((t) => ({ riskType: t, count: rows.filter((d) => d.riskType === t).length })).filter((r) => r.count > 0),
    topGu: top(rows.map((d) => d.input.gu)).map(([gu, count]) => ({ gu, count })),
    topService: top(rows.map((d) => d.input.serviceName)).map(([service, count]) => ({ service, count })),
  };
  rows.forEach((d) => stats.byLevel[d.riskLevel]++);

  let answer: string;
  if (rows.length === 0) {
    answer = levelFilter
      ? `아직 ${DIAG_GRADE[levelFilter].grade}등급 진단 기록이 없습니다. 사업장 진단을 몇 건 실행한 뒤 다시 질문해 주세요.`
      : '아직 진단 기록이 없습니다. 사업장 진단을 몇 건 실행한 뒤 다시 질문해 주세요.';
  } else {
    const target = levelFilter ? `${DIAG_GRADE[levelFilter].grade}등급 고객 ${rows.length}명` : `전체 고객 ${rows.length}명`;
    const mainType = [...stats.byRiskType].sort((a, b) => b.count - a.count)[0];
    answer = [
      `${target} 기준 분석입니다.`,
      mainType ? `- 가장 많은 추정 원인: ${RISK_TYPE_META[mainType.riskType].name} (${mainType.count}명)` : '',
      stats.topGu.length ? `- 많이 진단한 자치구: ${stats.topGu.map((g) => `${g.gu} ${g.count}명`).join(', ')}` : '',
      stats.topService.length ? `- 많이 진단한 업종: ${stats.topService.map((s) => `${s.service} ${s.count}명`).join(', ')}` : '',
      '실제 서비스에서는 이 집계를 근거로 LLM이 분석 문장을 작성합니다.',
    ].filter(Boolean).join('\n');
  }

  const res: InsightResponse = { answer, stats, generatedAt: new Date().toISOString() };
  return NextResponse.json(res);
}
