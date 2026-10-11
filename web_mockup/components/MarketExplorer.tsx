'use client';
import { useEffect, useMemo, useState } from 'react';
import SeoulMap, { type GuShape } from './SeoulMap';
import { ScopeChip, SignalBadge, SmallSampleBadge, Spec } from './badges';
import { Sparkline } from './charts';
import { getJSON, useMeta } from './useMeta';
import { MARKET_SIGNAL, fmtNum } from '@/lib/risk';
import type { CellPoint, CellResponse, DongRisk, DongsResponse, RegionRisk, RegionsResponse, Signal } from '@/lib/types';

type Mode = 'spec' | 'relative';

/** 상대 분위 모드: 현재 화면 집합 안에서 상위 15% RED, 15~40% YELLOW (데이터 분포 확인용 보조 기준) */
function relativeSignals<T>(rows: T[], get: (r: T) => number | null) {
  const vals = rows.map(get).filter((v): v is number => v != null).sort((a, b) => b - a);
  const qRed = vals[Math.floor(vals.length * 0.15)] ?? Infinity;
  const qYel = vals[Math.floor(vals.length * 0.4)] ?? Infinity;
  return (v: number | null): Signal | null => (v == null ? null : v >= qRed ? 'RED' : v >= qYel ? 'YELLOW' : 'GREEN');
}

export default function MarketExplorer({ geo }: { geo: { width: number; height: number; shapes: GuShape[] } }) {
  const meta = useMeta();
  const [f, setF] = useState({ qFrom: '', qTo: '', industry: '', service: '', minStores: 5 });
  const [mode, setMode] = useState<Mode>('spec');
  const [gu, setGu] = useState<string>('');
  const [regions, setRegions] = useState<RegionRisk[] | null>(null);
  const [dongs, setDongs] = useState<DongRisk[] | null>(null);
  const [dongCode, setDongCode] = useState('');
  const [svcList, setSvcList] = useState<{ code: string; name: string }[]>([]);
  const [cellSvc, setCellSvc] = useState('');
  const [cell, setCell] = useState<CellResponse | null>(null);
  const [explain, setExplain] = useState<{ text: string; cached: boolean } | null>(null);
  const [loadingExplain, setLoadingExplain] = useState(false);

  const qs = useMemo(() => {
    const p = new URLSearchParams();
    if (f.qFrom) p.set('qFrom', f.qFrom);
    if (f.qTo) p.set('qTo', f.qTo);
    if (f.industry) p.set('industry', f.industry);
    if (f.service) p.set('service', f.service);
    p.set('minStores', String(f.minStores));
    return p.toString();
  }, [f]);

  useEffect(() => { getJSON<RegionsResponse>(`/api/market/regions?${qs}`).then((r) => setRegions(r.regions)); }, [qs]);
  useEffect(() => {
    if (!gu) { setDongs(null); return; }
    getJSON<DongsResponse>(`/api/market/regions/${encodeURIComponent(gu)}/dongs?${qs}`).then((r) => setDongs(r.dongs));
  }, [gu, qs]);
  useEffect(() => { setExplain(null); }, [gu, f.industry]);
  useEffect(() => {
    if (!dongCode) return;
    getJSON<{ services: { code: string; name: string }[] }>(`/api/market/cells?dongCode=${dongCode}`).then((r) => {
      setSvcList(r.services);
      const pick = f.service && r.services.some((s) => s.code === f.service) ? f.service : r.services[0]?.code ?? '';
      setCellSvc(pick);
    });
  }, [dongCode, f.service]);
  useEffect(() => {
    if (!dongCode || !cellSvc) { setCell(null); return; }
    getJSON<CellResponse>(`/api/market/cells?dongCode=${dongCode}&service=${cellSvc}`).then(setCell).catch(() => setCell(null));
  }, [dongCode, cellSvc]);

  const regionSig = useMemo(() => {
    if (!regions) return {} as Record<string, Signal>;
    const rel = relativeSignals(regions, (r) => (r.obs ? r.riskWeight : null));
    return Object.fromEntries(regions.map((r) => [r.gu, (mode === 'spec' ? r.signal : rel(r.riskWeight)) as Signal]));
  }, [regions, mode]);
  const dongSig = useMemo(() => {
    if (!dongs) return (d: DongRisk) => d.signal;
    const rel = relativeSignals(dongs, (d) => d.riskWeight);
    return (d: DongRisk) => (mode === 'spec' ? d.signal : rel(d.riskWeight));
  }, [dongs, mode]);

  const sel = regions?.find((r) => r.gu === gu);
  const services = meta?.services.filter((s) => !f.industry || s.kosis === f.industry) ?? [];
  const sortedDongs = useMemo(() => [...(dongs ?? [])].sort((a, b) => (b.riskWeight ?? -1) - (a.riskWeight ?? -1)), [dongs]);
  const counts = Object.values(regionSig).reduce((a, s) => ({ ...a, [s]: (a[s] ?? 0) + 1 }), {} as Record<string, number>);

  async function runExplain() {
    if (!gu) return;
    setLoadingExplain(true);
    try { setExplain(await getJSON('/api/explain', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ gu, industry: f.industry || undefined }) })); }
    finally { setLoadingExplain(false); }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div className="row"><ScopeChip scope="market" /><Spec ids="F-MAP-01 · 02 · 03 · 06" /></div>
        <h1>상권 신호등</h1>
        <p>자치구를 누르면 행정동 성적표로, 행정동을 누르면 업종별 분기 상세로 내려갑니다.</p>
      </div>

      {/* F-MAP-06 공통 필터 — 지도·표·상세에 동시 적용 */}
      <section className="card" aria-label="필터">
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}>
          <div className="field"><label htmlFor="qf">기간 시작</label>
            <select id="qf" className="select" value={f.qFrom} onChange={(e) => setF({ ...f, qFrom: e.target.value })}>
              <option value="">{meta?.quarters[0] ?? '–'}</option>{meta?.quarters.map((q) => <option key={q}>{q}</option>)}
            </select></div>
          <div className="field"><label htmlFor="qt">기간 끝</label>
            <select id="qt" className="select" value={f.qTo} onChange={(e) => setF({ ...f, qTo: e.target.value })}>
              <option value="">{meta?.quarters.at(-1) ?? '–'}</option>{meta?.quarters.map((q) => <option key={q}>{q}</option>)}
            </select></div>
          <div className="field"><label htmlFor="gu">자치구</label>
            <select id="gu" className="select" value={gu} onChange={(e) => { setGu(e.target.value); setDongCode(''); }}>
              <option value="">전체</option>{meta?.gus.map((g) => <option key={g}>{g}</option>)}
            </select></div>
          <div className="field"><label htmlFor="ind">산업대분류</label>
            <select id="ind" className="select" value={f.industry} onChange={(e) => setF({ ...f, industry: e.target.value, service: '' })}>
              <option value="">전체</option>{meta?.industries.map((i) => <option key={i}>{i}</option>)}
            </select></div>
          <div className="field"><label htmlFor="svc">업종</label>
            <select id="svc" className="select" value={f.service} onChange={(e) => setF({ ...f, service: e.target.value })}>
              <option value="">전체</option>{services.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
            </select></div>
          <div className="field"><label htmlFor="min">최소 점포수</label>
            <input id="min" className="input" type="number" min={0} value={f.minStores} onChange={(e) => setF({ ...f, minStores: Math.max(0, Number(e.target.value)) })} />
            <span className="hint">기본 5 · 폐업률 200~300% 이상치 차단</span></div>
        </div>
      </section>

      <div className="grid-2">
        <section className="card">
          <div className="card-head">
            <div><h2>자치구 위험도</h2><p>위험가중치(업종 내 폐업률 percentile 평균) 기준 · <Spec ids="F-MAP-01" /></p></div>
            <div className="seg" role="group" aria-label="색 기준">
              <button aria-pressed={mode === 'spec'} onClick={() => setMode('spec')}>정의서 기준</button>
              <button aria-pressed={mode === 'relative'} onClick={() => setMode('relative')}>서울 내 상대</button>
            </div>
          </div>
          {regions ? (
            <SeoulMap {...geo} signals={regionSig} selected={gu}
              values={Object.fromEntries(regions.map((r) => [r.gu, `실질폐업률 ${r.realCloseRate.toFixed(2)}% · 가중치 ${r.riskWeight.toFixed(3)}`]))}
              onSelect={(g) => { setGu(g === gu ? '' : g); setDongCode(''); }} />
          ) : <p className="muted">불러오는 중…</p>}
          <div className="legend" style={{ marginTop: 10 }}>
            {(['GREEN', 'YELLOW', 'RED'] as Signal[]).map((s) => (
              <span key={s}><i className="sw" style={{ background: `var(--${s.toLowerCase()}-fill)` }} />{MARKET_SIGNAL[s].icon} {MARKET_SIGNAL[s].label} · {mode === 'spec' ? MARKET_SIGNAL[s].desc : s === 'RED' ? '상위 15%' : s === 'YELLOW' ? '상위 15~40%' : '나머지'} ({counts[s] ?? 0})</span>
            ))}
          </div>
          {mode === 'spec' && (counts.GREEN ?? 0) >= 24 && (
            <p className="notice notice-warn" style={{ marginTop: 10 }}>
              정의서 기준(0.60/0.85)으로는 거의 모든 자치구가 &lsquo;양호&rsquo;입니다. 위험가중치가 percentile 평균이라 자치구 단위에선 0.47~0.53에 몰리기 때문 — 임계값 재검토 필요. &lsquo;서울 내 상대&rsquo;로 분포를 비교해 보세요.
            </p>
          )}
        </section>

        <section className="card stack">
          <div className="card-head" style={{ marginBottom: 0 }}>
            <div><h2>{gu || '서울 전체'}</h2><p>{f.industry || '전 산업'} · {f.qFrom || meta?.quarters[0]} ~ {f.qTo || meta?.quarters.at(-1)}</p></div>
            {sel && <SignalBadge signal={regionSig[gu]} />}
          </div>
          {sel ? (
            <>
              <div className="stats">
                <div className="stat"><div className="k">실질폐업률 (가중)</div><div className="v">{sel.realCloseRate.toFixed(2)}%</div><div className="s">Σ폐업 ÷ Σ점포</div></div>
                <div className="stat"><div className="k">평균폐업률</div><div className="v" style={{ fontSize: 16 }}>{sel.avgCloseRate.toFixed(2)}%</div><div className="s">보조 지표</div></div>
                <div className="stat"><div className="k">위험가중치</div><div className="v" style={{ fontSize: 16 }}>{sel.riskWeight.toFixed(3)}</div></div>
                <div className="stat"><div className="k">점포수(분기 합)</div><div className="v" style={{ fontSize: 16 }}>{fmtNum(sel.stores)}</div></div>
              </div>
              <div className="stack" style={{ gap: 8 }}>
                <div className="row between"><h3>지표 해설</h3><Spec ids="F-LLM-04 · P2" /></div>
                {explain ? <p className="small">{explain.text} {explain.cached && <span className="badge badge-outline">캐시</span>}</p>
                  : <button className="btn btn-sm" onClick={runExplain} disabled={loadingExplain} style={{ justifySelf: 'start' }}>{loadingExplain ? '생성 중…' : 'AI 해설 보기'}</button>}
              </div>
            </>
          ) : (
            <>
              <p className="muted small">지도나 아래 표에서 자치구를 선택하세요. 표는 색을 못 구분해도 읽을 수 있는 대체 보기입니다.</p>
              <div className="table-wrap" style={{ maxHeight: 340 }}>
                <table>
                  <thead><tr><th>자치구</th><th>신호</th><th className="num">실질폐업률</th><th className="num">평균폐업률</th><th className="num">가중치</th></tr></thead>
                  <tbody>
                    {[...(regions ?? [])].sort((a, b) => b.realCloseRate - a.realCloseRate).map((r) => (
                      <tr key={r.gu} className="clickable" onClick={() => setGu(r.gu)}>
                        <td>{r.gu}</td><td><SignalBadge signal={regionSig[r.gu]} /></td>
                        <td className="num"><b>{r.realCloseRate.toFixed(2)}%</b></td><td className="num muted">{r.avgCloseRate.toFixed(2)}%</td><td className="num">{r.riskWeight.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </div>

      {gu && (
        <section className="card">
          <div className="card-head">
            <div><h2>{gu} 행정동 성적표</h2><p>행정동 × 산업대분류 · 관측 8건 이상 & 연점포수 100 이상만 값 표기 · <Spec ids="F-MAP-02" /></p></div>
            <span className="muted small">{dongs ? `${dongs.filter((d) => d.sufficient).length} / ${dongs.length} 조합 표기` : ''}</span>
          </div>
          <div className="table-wrap" style={{ maxHeight: 380 }}>
            <table>
              <thead><tr><th>행정동</th><th>산업대분류</th><th>신호</th><th className="num">위험가중치</th><th className="num">평균폐업률</th><th className="num">폐업개업격차</th><th className="num">관측</th><th className="num">연점포수</th></tr></thead>
              <tbody>
                {sortedDongs.map((d) => (
                  <tr key={d.dongCode + d.industry} className="clickable" aria-selected={d.dongCode === dongCode} onClick={() => setDongCode(d.dongCode)}>
                    <td>{d.dong}</td><td className="muted">{d.industry}</td><td><SignalBadge signal={dongSig(d)} /></td>
                    <td className="num">{d.riskWeight?.toFixed(3) ?? '–'}</td><td className="num">{d.avgCloseRate != null ? `${d.avgCloseRate.toFixed(2)}%` : '–'}</td>
                    <td className="num">{d.closeOpenGap != null ? `${d.closeOpenGap > 0 ? '+' : ''}${d.closeOpenGap.toFixed(2)}` : '–'}</td>
                    <td className="num muted">{d.obsQuarters}</td><td className="num muted">{fmtNum(d.storeYears)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {dongCode && (
        <section className="card">
          <div className="card-head">
            <div><h2>{cell?.dong ?? ''} · 업종 상세</h2><p>분기별 점포수·폐업률·개업률·격차·업종내 percentile · <Spec ids="F-MAP-03" /></p></div>
            <div className="field" style={{ minWidth: 200 }}>
              <label htmlFor="cs" className="sr-only">업종 선택</label>
              <select id="cs" className="select" value={cellSvc} onChange={(e) => setCellSvc(e.target.value)}>
                {svcList.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
              </select>
            </div>
          </div>
          {cell && (
            <>
              <div className="stats" style={{ marginBottom: 12 }}>
                {([['점포수', (p: CellPoint) => p.stores, ''], ['폐업률', (p: CellPoint) => p.closeRate, '%'], ['개업률', (p: CellPoint) => p.openRate, '%'], ['업종내 percentile', (p: CellPoint) => p.percentile, '']] as const).map(([k, get, u]) => {
                  const vals = cell.series.map(get);
                  const last = [...vals].reverse().find((v) => v != null);
                  return (
                    <div key={k} className="stat">
                      <div className="k">{k} (최근)</div>
                      <div className="row between" style={{ flexWrap: 'nowrap' }}>
                        <div className="v" style={{ fontSize: 18 }}>{last == null ? '–' : `${u === '%' ? last.toFixed(1) : k === '점포수' ? last : last.toFixed(2)}${u}`}</div>
                        <Sparkline values={vals} label={`${k} 11개 분기 추이`} w={84} h={28} />
                      </div>
                    </div>
                  );
                })}
              </div>
              {cell.series.some((p) => p.smallSample && p.stores != null) && (
                <p className="notice notice-warn" style={{ marginBottom: 10 }}>점포수 5개 이하 분기는 폐업률이 0/33/67%처럼 계단값으로 튑니다. 해당 분기는 &lsquo;표본 적음&rsquo;으로 표시했습니다.</p>
              )}
              <div className="table-wrap">
                <table>
                  <thead><tr><th>분기</th><th className="num">점포수</th><th className="num">폐업률</th><th className="num">개업률</th><th className="num">격차</th><th className="num">percentile</th><th></th></tr></thead>
                  <tbody>
                    {cell.series.map((p) => (
                      <tr key={p.quarter}>
                        <td>{p.quarter}</td><td className="num">{p.stores ?? '–'}</td>
                        <td className="num">{p.closeRate != null ? `${p.closeRate}%` : '–'}</td><td className="num">{p.openRate != null ? `${p.openRate}%` : '–'}</td>
                        <td className="num">{p.closeOpenGap ?? '–'}</td><td className="num">{p.percentile?.toFixed(3) ?? '–'}</td>
                        <td>{p.stores != null && p.smallSample && <SmallSampleBadge />}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
}
