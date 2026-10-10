'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { GradeBadge, ScopeChip, Spec } from './badges';
import { PositionHistogram, Sparkline } from './charts';
import Markdown from './Markdown';
import MethodPanel from './MethodPanel';
import { getJSON } from './useMeta';
import { DIAG_GRADE, RISK_TYPE_META, RISK_TYPES } from '@/lib/risk';
import type { Signal, SignalResponse, Solution } from '@/lib/types';

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const LV_COLOR: Record<Signal, string> = { GREEN: 'var(--green-fill)', YELLOW: 'var(--yellow-fill)', RED: 'var(--red-fill)' };

export function SolutionCard({ s }: { s: Solution }) {
  return (
    <article className="sol">
      <div className="row between"><span className="badge badge-outline">{s.agency}</span><span className="spec-tag">{s.solutionId}</span></div>
      <h3>{s.title}</h3>
      <p className="small muted">{s.summary}</p>
      <dl><dt>한도</dt><dd>{s.limit}</dd><dt>금리</dt><dd>{s.rate}</dd></dl>
      {s.url ? <a className={`btn btn-sm ${s.actionType === 'APPLY_NOW' ? 'btn-primary' : ''}`} href={s.url} target="_blank" rel="noreferrer">{s.actionLabel}</a>
        : <button className={`btn btn-sm ${s.actionType === 'APPLY_NOW' ? 'btn-primary' : ''}`} disabled title="공고 URL 미등록 (F-RAG-02 메타 태깅 필요)">{s.actionLabel}</button>}
    </article>
  );
}

function ReportBox({ id }: { id: string }) {
  const [text, setText] = useState('');
  const [state, setState] = useState<'idle' | 'streaming' | 'done'>('idle');
  const [meta, setMeta] = useState<{ cache: string; guard: string } | null>(null);
  async function start() {
    setText(''); setState('streaming');
    const res = await fetch('/api/report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ diagnosisId: id }) });
    setMeta({ cache: res.headers.get('X-Report-Cache') ?? '', guard: res.headers.get('X-Guardrail') ?? '' });
    const reader = res.body!.getReader(); const dec = new TextDecoder();
    for (;;) { const { done, value } = await reader.read(); if (done) break; setText((t) => t + dec.decode(value, { stream: true })); }
    setState('done');
  }
  const [pass, n] = (meta?.guard ?? '').split(';');
  return (
    <section className="card">
      <div className="card-head">
        <div><h2>AI 진단 리포트</h2><p>진단 결과와 추천 문서만 근거로 작성 · <Spec ids="F-LLM-01 · 02 · 05 · F-SYS-07" /></p></div>
        <div className="row">
          {state === 'done' && meta && <span className={`badge ${pass === 'PASS' ? 'badge-GREEN' : 'badge-RED'}`}>{pass === 'PASS' ? `✓ 수치 대조 검증 통과 (${n}개)` : '✕ 검증 실패 → 템플릿 폴백'}</span>}
          {state === 'done' && meta && <span className="badge badge-outline" title="등급·유형 설명과 지원사업 안내문만 (등급, 유형, 업종, 자치구) 키로 캐싱">공통문단 캐시 {meta.cache}</span>}
        </div>
      </div>
      {state === 'idle' ? <button className="btn btn-primary" onClick={start}>리포트 생성하기</button>
        : <Markdown text={text} streaming={state === 'streaming'} />}
      {state === 'done' && <button className="btn btn-sm" style={{ marginTop: 12 }} onClick={start}>다시 생성</button>}
    </section>
  );
}

function ChatBox({ id }: { id: string }) {
  const [msgs, setMsgs] = useState<{ role: 'user' | 'assistant'; text: string }[]>([]);
  const [q, setQ] = useState('');
  const [left, setLeft] = useState(5);
  const [err, setErr] = useState('');
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => { box.current?.scrollTo({ top: 1e6, behavior: 'smooth' }); }, [msgs]);
  async function ask(question: string) {
    if (!question.trim()) return;
    setErr(''); setMsgs((m) => [...m, { role: 'user', text: question }]); setQ('');
    try {
      const r = await getJSON<{ answer: string; remaining: number }>('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ diagnosisId: id, question }) });
      setMsgs((m) => [...m, { role: 'assistant', text: r.answer }]); setLeft(r.remaining);
    } catch (e) { setErr((e as Error).message); setLeft(0); }
  }
  return (
    <section className="card stack">
      <div className="card-head" style={{ marginBottom: 0 }}><div><h2>궁금한 점 물어보기</h2><p>남은 질문 {left}개 · <Spec ids="F-LLM-03 · P1" /></p></div></div>
      {msgs.length > 0 && <div className="chat" ref={box} aria-live="polite">{msgs.map((m, i) => <div key={i} className={`msg msg-${m.role}`}>{m.text}</div>)}</div>}
      {msgs.length === 0 && (
        <div className="row">{['왜 이 등급이 나왔나요?', '위험 점수는 어떻게 계산했나요?', '지원사업은 어디서 신청하나요?'].map((s) => <button key={s} className="btn btn-sm" onClick={() => ask(s)}>{s}</button>)}</div>
      )}
      <form className="row" style={{ flexWrap: 'nowrap' }} onSubmit={(e) => { e.preventDefault(); ask(q); }}>
        <label htmlFor="q" className="sr-only">질문</label>
        <input id="q" className="input" placeholder="진단 결과에 대해 질문하세요" value={q} onChange={(e) => setQ(e.target.value)} disabled={left <= 0} />
        <button className="btn btn-primary" disabled={left <= 0 || !q.trim()}>보내기</button>
      </form>
      {err && <p className="error">{err}</p>}
    </section>
  );
}

function ShareBox({ d }: { d: SignalResponse }) {
  const [copied, setCopied] = useState(false);
  const url = typeof window !== 'undefined' ? `${window.location.origin}/share/${d.shareToken}` : '';
  return (
    <section className="card stack">
      <div className="card-head" style={{ marginBottom: 0 }}><div><h2>결과 저장·공유</h2><p>비로그인 임시 링크 · {new Date(d.expiresAt).toLocaleString('ko-KR')}까지 · <Spec ids="F-DIA-08 · P2" /></p></div></div>
      <div className="row" style={{ flexWrap: 'nowrap' }}>
        <input className="input" readOnly value={url} aria-label="공유 링크" onFocus={(e) => e.target.select()} />
        <button className="btn" onClick={() => { navigator.clipboard?.writeText(url); setCopied(true); }}>{copied ? '복사됨' : '복사'}</button>
      </div>
      <p className="hint">링크를 받은 사람은 진단 등급·추정 원인·지원사업만 볼 수 있고, 매출 지수·위험 점수·상권 위치는 볼 수 없습니다. 진단 ID: {d.diagnosisId}</p>
    </section>
  );
}

export default function DiagnosisResult({ id }: { id: string }) {
  const [d, setD] = useState<SignalResponse | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { getJSON<SignalResponse>(`/api/diagnosis/${id}`).then(setD).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <div className="page"><p className="notice notice-danger">{err}</p><Link href="/diagnosis" className="btn" style={{ justifySelf: 'start' }}>다시 진단하기</Link></div>;
  if (!d) return <div className="page"><p className="muted">불러오는 중…</p></div>;

  const g = DIAG_GRADE[d.riskLevel];
  const meta = RISK_TYPE_META[d.riskType];
  const typesSorted = [...RISK_TYPES].sort((a, b) => d.typeProbs[b] - d.typeProbs[a]);

  return (
    <div className="page">
      <div className="page-head">
        <div className="row"><ScopeChip scope="diag" /><Spec ids="F-DIA-03~07 · F-RAG-04" /></div>
        <h1>{d.input.dong} {d.input.serviceName} 진단 결과</h1>
        <p>{d.input.gu} · {d.input.industry} · 상권 데이터 기준 {d.features.asOf}</p>
      </div>

      <div className="grid-2">
        <section className="card stack">
          <div className="grade-hero">
            <div className={`grade-mark grade-${d.riskLevel} anim-${d.visualTheme.animation}`} role="img" aria-label={`진단 등급 ${g.grade} ${g.label}`}>
              {g.grade}<small>{g.label}</small>
            </div>
            <div className="stack" style={{ gap: 6 }}>
              <span className="small muted">사업장 진단 등급</span>
              <h2 style={{ fontSize: 22 }}>{d.visualTheme.impactMessage}</h2>
              <div className="row"><GradeBadge level={d.riskLevel} /><span className="badge badge-brand" title="학습 RED 30% → 실제 14% 기준으로 재계산">사전확률 보정 적용</span></div>
            </div>
          </div>
          <div className="stack" style={{ gap: 6 }}>
            {(['GREEN', 'YELLOW', 'RED'] as Signal[]).map((lv) => (
              <div className="pbar" key={lv}>
                <span>{DIAG_GRADE[lv].icon} {DIAG_GRADE[lv].grade} · {DIAG_GRADE[lv].label}</span>
                <span className="track"><span className="fill" style={{ display: 'block', width: pct(d.levelProbs[lv]), background: LV_COLOR[lv] }} /></span>
                <b className="num" style={{ textAlign: 'right' }}>{pct(d.levelProbs[lv])}</b>
              </div>
            ))}
          </div>
          {d.riskLevel === 'YELLOW' && <p className="notice notice-warn">B등급은 모델 재현율이 33.9%로 신뢰도가 낮습니다. 참고용으로만 봐 주세요.</p>}
        </section>

        <section className="card stack">
          <div className="stats" style={{ gridTemplateColumns: 'repeat(2, minmax(0,1fr))' }}>
            <div className="stat">
              <div className="k">위험 점수 <Spec ids="F-DIA-06" /></div>
              <div className="v">{d.score}<span className="small muted"> / 100</span></div>
              <div className="s">{d.scoreMethod === 'six_month_drop' ? '이전 3개월 대비 감소율' : '3개월 기울기 기반 대체 산식'}</div>
            </div>
            <div className="stat">
              <div className="k">매출 지수 (1개월차=100)</div>
              <div className="row between" style={{ flexWrap: 'nowrap' }}><div className="v" style={{ fontSize: 18 }}>{d.revenueIndex[2]}</div><Sparkline values={d.revenueIndex} label="3개월 매출 지수" w={80} h={28} /></div>
              <div className="s num">{d.revenueIndex.join(' → ')}</div>
            </div>
          </div>
          {d.scoreMethod === 'three_month_slope' && <p className="hint">이전 3개월 매출이 없어 기울기 기반 산식을 썼습니다 (응답 flag: three_month_slope).</p>}
          <div>
            <div className="row between"><h3>상권 대비 위치</h3><Spec ids="F-DIA-07" /></div>
            <p className="small" style={{ margin: '4px 0 6px' }}><b>{d.context.sentence}</b></p>
            <PositionHistogram hist={d.context.hist} percentile={d.context.percentile} label={d.context.sentence} />
            <p className="hint">같은 업종·같은 분기 행정동들의 폐업률 percentile 분포. 상권 통계 기준이며 내 가게 매출과는 별개입니다.</p>
          </div>
        </section>
      </div>

      <section className="card">
        <div className="card-head">
          <div><h2>추정 원인 <span className="badge badge-outline" style={{ verticalAlign: 'middle' }}>확정 진단 아님</span></h2><p>6개 유형별 확률 · <Spec ids="F-DIA-05" /></p></div>
          <span className="badge" style={{ background: 'var(--surface-2)' }}>가장 가능성 높은 유형: <b>&nbsp;{meta.name}</b></span>
        </div>
        <div className="stack" style={{ gap: 6 }}>
          {typesSorted.map((t) => {
            const m = RISK_TYPE_META[t];
            return (
              <div className="pbar" key={t} style={{ gridTemplateColumns: '140px 1fr 52px' }}>
                <span style={{ fontWeight: t === d.riskType ? 800 : 500 }}>{m.name}</span>
                <span className="track"><span className="fill" style={{ display: 'block', width: pct(d.typeProbs[t]), background: LV_COLOR[m.level], opacity: t === d.riskType ? 1 : 0.55 }} /></span>
                <b className="num" style={{ textAlign: 'right' }}>{pct(d.typeProbs[t])}</b>
              </div>
            );
          })}
        </div>
        {meta.recall != null && meta.recall < 0.05 && (
          <p className="notice notice-warn" style={{ marginTop: 10 }}>&lsquo;{meta.name}&rsquo;은 현재 모델 재현율이 {(meta.recall * 100).toFixed(1)}%입니다. 이 유형 판정은 특히 신중하게 해석해 주세요.</p>
        )}
      </section>

      <section className="card">
        <div className="card-head"><div><h2>맞춤 지원사업</h2><p>추정 원인 유형으로 검색한 2026년 정책자금 · <Spec ids="F-RAG-03 · 04" /></p></div></div>
        {d.solutions.length ? (
          <div className="grid-3">{d.solutions.map((s) => <SolutionCard key={s.solutionId} s={s} />)}</div>
        ) : <p className="notice">현재 진단 유형(정상 유지형)에 연결된 지원사업 문서가 없습니다. 운영 화면의 문서 커버리지를 확인하세요.</p>}
      </section>

      <ReportBox id={d.diagnosisId} />
      <div className="grid-2" style={{ gridTemplateColumns: undefined }}>
        <ChatBox id={d.diagnosisId} />
        <ShareBox d={d} />
      </div>
      <MethodPanel />
      <p className="notice small">※ 매출 시계열은 시뮬레이션 기반이며, 정확도는 시뮬레이션 규칙 복원율입니다. 지원사업의 자격·한도·금리·신청기간은 반드시 소관기관 공고에서 최종 확인하세요. <Spec ids="F-LLM-05" /></p>
    </div>
  );
}
