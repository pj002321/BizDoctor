'use client';
import { useState } from 'react';
import { Spec } from './badges';
import { getJSON } from './useMeta';
import { DIAG_GRADE, RISK_TYPE_META } from '@/lib/risk';
import type { InsightResponse } from '@/lib/types';

const EXAMPLES = ['C등급 고객의 공통점은?', '어느 업종이 진단을 많이 받았나요?', '전체 고객 현황을 요약해 줘'];

export default function AdminInsights() {
  const [q, setQ] = useState('');
  const [res, setRes] = useState<InsightResponse | null>(null);
  const [asked, setAsked] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  async function ask(question: string) {
    if (!question.trim() || loading) return;
    setErr('');
    setLoading(true);
    setAsked(question);
    try {
      setRes(await getJSON<InsightResponse>('/api/admin/insights', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      }));
      setQ('');
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <span className="badge badge-outline" style={{ justifySelf: 'start' }}>내부 운영 화면</span>
        <h1>고객 분석 AI</h1>
        <p>진단 기록을 바탕으로 고객 현황을 질문하면 분석해 드립니다. <Spec ids="POST /api/admin/insights" /></p>
      </div>

      <section className="card stack">
        <div className="row">{EXAMPLES.map((s) => <button key={s} className="btn btn-sm" onClick={() => ask(s)}>{s}</button>)}</div>
        <form className="row" style={{ flexWrap: 'nowrap' }} onSubmit={(e) => { e.preventDefault(); ask(q); }}>
          <label htmlFor="insight-q" className="sr-only">질문</label>
          <input id="insight-q" className="input" placeholder="예: 이번 주 C등급 고객이 많은 지역은?" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="btn btn-primary" disabled={loading || !q.trim()}>{loading ? '분석 중…' : '분석하기'}</button>
        </form>
        {err && <p className="error" role="alert">{err}</p>}
      </section>

      {res && (
        <section className="card stack">
          <div className="card-head" style={{ marginBottom: 0 }}>
            <div><h2>분석 결과</h2><p>질문: {asked} · {new Date(res.generatedAt).toLocaleString('ko-KR')}</p></div>
          </div>
          <p style={{ whiteSpace: 'pre-line' }}>{res.answer}</p>
          {res.stats.total > 0 && (
            <div className="stats">
              <div className="stat"><div className="k">대상 고객</div><div className="v">{res.stats.total}명</div></div>
              <div className="stat"><div className="k">등급 분포</div><div className="v" style={{ fontSize: 15 }}>
                {(['GREEN', 'YELLOW', 'RED'] as const).map((l) => `${DIAG_GRADE[l].grade} ${res.stats.byLevel[l]}`).join(' · ')}
              </div></div>
              <div className="stat"><div className="k">추정 원인</div><div className="v" style={{ fontSize: 13 }}>
                {res.stats.byRiskType.map((r) => `${RISK_TYPE_META[r.riskType].name} ${r.count}`).join(', ')}
              </div></div>
              <div className="stat"><div className="k">상위 업종</div><div className="v" style={{ fontSize: 13 }}>
                {res.stats.topService.map((s) => `${s.service} ${s.count}`).join(', ')}
              </div></div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
