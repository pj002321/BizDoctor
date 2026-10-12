// GET /api/admin/metrics — F-SYS-06 로깅·모니터링 (목업: 인메모리 카운터)
import { NextResponse } from 'next/server';
import { POLICY_DOCS } from '@/lib/policies';
import { REAL_RED_RATE, RISK_TYPES } from '@/lib/risk';
import { store } from '@/lib/store';

export async function GET() {
  const m = store.metrics;
  const total = m.levelCount.GREEN + m.levelCount.YELLOW + m.levelCount.RED;
  const redShare = total ? m.levelCount.RED / total : 0;
  return NextResponse.json({
    ...m,
    redShare,
    redAlarm: total >= 20 && Math.abs(redShare - REAL_RED_RATE) > 0.1, // 사전확률 대비 ±10%p 이탈 시 보정 오류 알람
    ragEmptyRate: m.ragQueries ? m.ragEmpty / m.ragQueries : 0,
    coverage: RISK_TYPES.map((t) => ({ riskType: t, docs: POLICY_DOCS.filter((d) => d.riskTypeTags.includes(t)).length })), // F-RAG-02
    cacheEntries: store.reportCache.size,
  });
}
