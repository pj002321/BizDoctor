'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ScopeChip, Spec } from './badges';
import { getJSON, useMeta } from './useMeta';
import type { SignalResponse } from '@/lib/types';

const toNum = (s: string) => Number(s.replace(/[^\d]/g, '')) || 0;
const fmt = (s: string) => { const n = toNum(s); return n ? n.toLocaleString('ko-KR') : ''; };

export default function DiagnosisForm() {
  const meta = useMeta();
  const router = useRouter();
  const [gu, setGu] = useState('');
  const [dong, setDong] = useState('');
  const [svc, setSvc] = useState('');
  const [svcList, setSvcList] = useState<{ code: string; name: string }[]>([]);
  const [rev, setRev] = useState(['', '', '']);
  const [usePrev, setUsePrev] = useState(false);
  const [prev, setPrev] = useState(['', '', '']);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [pendingSvc, setPendingSvc] = useState('');

  useEffect(() => {
    setSvc(''); setSvcList([]);
    if (dong) getJSON<{ services: { code: string; name: string }[] }>(`/api/market/cells?dongCode=${dong}`).then((r) => {
      setSvcList(r.services);
      if (pendingSvc && r.services.some((s) => s.code === pendingSvc)) { setSvc(pendingSvc); setPendingSvc(''); }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dong]);

  const nums = rev.map(toNum);
  const idx = nums[0] ? nums.map((v) => Math.round((v / nums[0]) * 1000) / 10) : null;

  function fillExample() {
    setGu('관악구');
    const d = meta?.dongs.find((x) => x.name === '신림동' && x.gu === '관악구') ?? meta?.dongs.find((x) => x.gu === '관악구');
    if (d) setDong(d.code);
    setRev(['12,400,000', '11,100,000', '9,300,000']);
    setPendingSvc('CS100001'); // 한식음식점
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr('');
    if (!dong || !svc) return setErr('행정동과 업종을 선택해 주세요.');
    if (nums.some((n) => n <= 0)) return setErr('최근 3개월 매출을 모두 입력해 주세요.');
    setBusy(true);
    try {
      const body = { dongCode: dong, service: svc, revenue: nums, ...(usePrev && prev.every((p) => toNum(p) > 0) ? { prevRevenue: prev.map(toNum) } : {}) };
      const res = await getJSON<SignalResponse>('/api/diagnosis', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      router.push(`/diagnosis/${res.diagnosisId}`);
    } catch (e) { setErr((e as Error).message); setBusy(false); }
  }

  const months = ['3개월 전', '2개월 전', '지난달'];
  return (
    <div className="page" style={{ maxWidth: 760 }}>
      <div className="page-head">
        <div className="row"><ScopeChip scope="diag" /><Spec ids="F-DIA-01 · F-SYS-05" /></div>
        <h1>사업장 진단</h1>
        <p>가게 위치와 업종, 최근 3개월 매출만 있으면 됩니다. 1분 정도 걸려요.</p>
      </div>
      <form className="card stack" onSubmit={submit} noValidate>
        <div className="row between"><h2>1. 가게 위치와 업종</h2><button type="button" className="btn btn-sm" onClick={fillExample}>예시 값 채우기</button></div>
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
          <div className="field"><label htmlFor="gu">자치구</label>
            <select id="gu" className="select" value={gu} onChange={(e) => { setGu(e.target.value); setDong(''); }}>
              <option value="">선택</option>{meta?.gus.map((g) => <option key={g}>{g}</option>)}
            </select></div>
          <div className="field"><label htmlFor="dong">행정동</label>
            <select id="dong" className="select" value={dong} onChange={(e) => setDong(e.target.value)} disabled={!gu}>
              <option value="">선택</option>{meta?.dongs.filter((d) => d.gu === gu).map((d) => <option key={d.code} value={d.code}>{d.name}</option>)}
            </select></div>
          <div className="field"><label htmlFor="svc">업종</label>
            <select id="svc" className="select" value={svc} onChange={(e) => setSvc(e.target.value)} disabled={!svcList.length}>
              <option value="">선택</option>{svcList.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
            </select>
            <span className="hint">해당 행정동에 상권 데이터가 있는 업종만 표시</span></div>
        </div>

        <h2 style={{ marginTop: 8 }}>2. 최근 3개월 월매출</h2>
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
          {months.map((m, i) => (
            <div className="field" key={m}><label htmlFor={`r${i}`}>{m} (원)</label>
              <input id={`r${i}`} className="input num" inputMode="numeric" placeholder="예: 12,000,000" value={rev[i]}
                onChange={(e) => setRev(rev.map((v, j) => (j === i ? fmt(e.target.value) : v)))} /></div>
          ))}
        </div>
        <div className="notice notice-info small">
          <b>금액은 저장되지 않습니다.</b> 3개월 전 매출을 100으로 둔 지수로 바꿔 계산에만 쓰고, 서버에는 지수만 남깁니다.
          {idx && <div style={{ marginTop: 6 }}>모델에 전달되는 값: <b className="num">{idx.join(' → ')}</b></div>}
        </div>
        <label className="row small" style={{ cursor: 'pointer' }}>
          <input type="checkbox" checked={usePrev} onChange={(e) => setUsePrev(e.target.checked)} />
          그 이전 3개월 매출도 입력하기 (위험 점수를 표준 산식으로 계산) <Spec ids="F-DIA-06" />
        </label>
        {usePrev && (
          <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
            {['6개월 전', '5개월 전', '4개월 전'].map((m, i) => (
              <div className="field" key={m}><label htmlFor={`p${i}`}>{m} (원)</label>
                <input id={`p${i}`} className="input num" inputMode="numeric" value={prev[i]} onChange={(e) => setPrev(prev.map((v, j) => (j === i ? fmt(e.target.value) : v)))} /></div>
            ))}
          </div>
        )}
        {err && <p className="error" role="alert">{err}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? '진단 중…' : '진단 결과 보기'}</button>
      </form>
    </div>
  );
}
