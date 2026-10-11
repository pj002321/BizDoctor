// POST /api/report { diagnosisId } — F-LLM-01 진단 리포트 (스트리밍)
import { NextRequest, NextResponse } from 'next/server';
import { buildReport } from '@/lib/report';
import { getDiagnosis, store } from '@/lib/store';

export async function POST(req: NextRequest) {
  const { diagnosisId } = await req.json();
  const d = getDiagnosis(diagnosisId);
  if (!d) return NextResponse.json({ error: '진단 결과가 없습니다.' }, { status: 404 });
  const { report, cacheHit, check } = buildReport(d);
  store.metrics.llmTokens += Math.round(report.length / 2); // 대략적인 토큰 추정 (목업)

  const enc = new TextEncoder();
  const chunks = report.match(/[\s\S]{1,12}/g) ?? [];
  const stream = new ReadableStream({
    async start(controller) {
      await new Promise((r) => setTimeout(r, 400)); // 첫 토큰 지연 흉내 (목표 < 3s)
      for (const c of chunks) {
        controller.enqueue(enc.encode(c));
        await new Promise((r) => setTimeout(r, 18));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'X-Report-Cache': cacheHit ? 'HIT' : 'MISS',
      'X-Guardrail': check.ok ? `PASS;${check.checkedNumbers}` : `FAIL;${check.badNums.join(',')}`,
    },
  });
}
