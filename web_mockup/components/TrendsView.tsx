'use client';
import { useEffect, useMemo, useState } from 'react';
import { LineChart, INDUSTRY_ORDER, industryColor } from './charts';
import { ScopeChip, Spec } from './badges';
import { getJSON } from './useMeta';
import type { TrendsResponse } from '@/lib/types';

export default function TrendsView({ weights }: { weights: Record<string, Record<string, number>> }) {
  const [data, setData] = useState<TrendsResponse | null>(null);
  const [picked, setPicked] = useState<string[]>(['숙박 및 음식점업', '도매 및 소매업', '부동산업']);
  const [view, setView] = useState<'all' | 'by'>('all');
  const [table, setTable] = useState(false);
  useEffect(() => { getJSON<TrendsResponse>('/api/market/trends').then(setData); }, []);

  const quarters = useMemo(() => [...new Set(data?.series.map((s) => s.quarter) ?? [])], [data]);
  const annotations = (data?.annotations ?? []).map((a) => ({ index: quarters.indexOf(a.quarter), label: a.label })).filter((a) => a.index >= 0);

  // 전체: 산업별 값을 분기 점포수로 가중 평균
  const overall = useMemo(() => {
    if (!data) return null;
    const by = (key: 'avgCloseRate' | 'avgOpenRate') => quarters.map((q) => {
      const rows = data.series.filter((s) => s.quarter === q);
      const w = rows.reduce((a, r) => a + (weights[q]?.[r.industry] ?? 0), 0);
      return +(rows.reduce((a, r) => a + r[key] * (weights[q]?.[r.industry] ?? 0), 0) / w).toFixed(2);
    });
    return { close: by('avgCloseRate'), open: by('avgOpenRate') };
  }, [data, quarters, weights]);

  const lines = (key: 'avgCloseRate' | 'avgOpenRate') => picked.map((ind) => ({
    name: ind, color: industryColor(ind),
    values: quarters.map((q) => data?.series.find((s) => s.quarter === q && s.industry === ind)?.[key] ?? null),
  }));

  return (
    <div className="page">
      <div className="page-head">
        <div className="row"><ScopeChip scope="market" /><Spec ids="F-MAP-04 · P1" /></div>
        <h1>분기별 산업 추이</h1>
        <p>2023 Q1 ~ 2025 Q3 폐업률·개업률. 2024년 1분기부터 폐업률이 개업률을 앞지르기 시작했습니다.</p>
      </div>
      <section className="card">
        <div className="card-head">
          <div className="seg" role="group" aria-label="보기">
            <button aria-pressed={view === 'all'} onClick={() => setView('all')}>서울 전체</button>
            <button aria-pressed={view === 'by'} onClick={() => setView('by')}>산업별 비교</button>
          </div>
          <button className="btn btn-sm" onClick={() => setTable(!table)}>{table ? '차트로 보기' : '표로 보기'}</button>
        </div>
        {view === 'by' && (
          <div className="row" style={{ marginBottom: 12 }}>
            {INDUSTRY_ORDER.map((ind) => {
              const on = picked.includes(ind);
              return (
                <button key={ind} className="btn btn-sm" aria-pressed={on} onClick={() => setPicked(on ? picked.filter((p) => p !== ind) : [...picked, ind])}
                  style={{ borderColor: on ? industryColor(ind) : undefined, background: on ? 'var(--surface-2)' : undefined }}>
                  <i className="sw" style={{ background: on ? industryColor(ind) : 'var(--na-fill)' }} />{ind}
                </button>
              );
            })}
          </div>
        )}
        {!data || !overall ? <p className="muted">불러오는 중…</p> : table ? (
          <div className="table-wrap" style={{ maxHeight: 420 }}>
            <table>
              <thead><tr><th>분기</th><th>산업대분류</th><th className="num">평균폐업률</th><th className="num">평균개업률</th><th className="num">실질폐업률</th></tr></thead>
              <tbody>{data.series.filter((s) => view === 'all' || picked.includes(s.industry)).map((s) => (
                <tr key={s.quarter + s.industry}><td>{s.quarter}</td><td>{s.industry}</td><td className="num">{s.avgCloseRate}%</td><td className="num">{s.avgOpenRate}%</td><td className="num">{s.realCloseRate}%</td></tr>
              ))}</tbody>
            </table>
          </div>
        ) : view === 'all' ? (
          <LineChart labels={quarters} annotations={annotations} yTitle="폐업률·개업률"
            series={[{ name: '평균폐업률', color: '#e34948', values: overall.close }, { name: '평균개업률', color: '#2a78d6', values: overall.open }]} />
        ) : (
          <div className="stack" style={{ gap: 20 }}>
            <div><h3 style={{ marginBottom: 6 }}>평균폐업률</h3><LineChart labels={quarters} annotations={annotations} series={lines('avgCloseRate')} height={240} yTitle="폐업률" /></div>
            <div><h3 style={{ marginBottom: 6 }}>평균개업률</h3><LineChart labels={quarters} annotations={annotations} series={lines('avgOpenRate')} height={240} yTitle="개업률" /></div>
          </div>
        )}
        <p className="tiny muted" style={{ marginTop: 10 }}>서울 전체 = 산업대분류별 평균을 분기 점포수로 가중 평균. 두 지표는 같은 단위(%)라 한 축에 표시.</p>
      </section>
    </div>
  );
}
