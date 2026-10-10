'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { GradeBadge, ScopeChip, Spec } from './badges';
import { SolutionCard } from './DiagnosisResult';
import { getJSON } from './useMeta';
import { RISK_TYPE_META } from '@/lib/risk';
import type { SharedDiagnosis } from '@/lib/types';

export default function SharedView({ token }: { token: string }) {
  const [d, setD] = useState<SharedDiagnosis | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { getJSON<SharedDiagnosis>(`/api/diagnosis/shared?token=${token}`).then(setD).catch((e) => setErr(e.message)); }, [token]);
  if (err) return <div className="page"><p className="notice notice-danger">{err}</p></div>;
  if (!d) return <div className="page"><p className="muted">불러오는 중…</p></div>;
  const m = RISK_TYPE_META[d.riskType];
  return (
    <div className="page" style={{ maxWidth: 880 }}>
      <div className="page-head">
        <div className="row"><ScopeChip scope="diag" /><span className="badge badge-outline">공유된 결과 · 읽기 전용</span><Spec ids="F-DIA-08" /></div>
        <h1>{d.input.dong} {d.input.serviceName} 진단 결과</h1>
        <p>{new Date(d.expiresAt).toLocaleString('ko-KR')}까지 열람 가능</p>
      </div>
      <section className="card stack">
        <div className="row"><GradeBadge level={d.riskLevel} /><span className="small">추정 원인: <b>{m.name}</b> ({(d.typeProbs[d.riskType] * 100).toFixed(1)}%)</span></div>
        <p className="notice small">공유 링크에서는 매출 지수, 위험 점수, 상권 내 위치 등 매출 관련 수치가 표시되지 않습니다.</p>
      </section>
      {d.solutions.length > 0 && <div className="grid-3">{d.solutions.map((s) => <SolutionCard key={s.solutionId} s={s} />)}</div>}
      <Link href="/diagnosis" className="btn btn-primary" style={{ justifySelf: 'start' }}>내 가게도 진단하기</Link>
    </div>
  );
}
