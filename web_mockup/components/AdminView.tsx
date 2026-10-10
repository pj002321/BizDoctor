'use client';
import { useEffect, useState } from 'react';
import { Spec } from './badges';
import { getJSON } from './useMeta';
import { RISK_TYPE_META } from '@/lib/risk';
import type { PolicyDoc } from '@/lib/policies';
import type { RiskType, Signal } from '@/lib/types';

interface M {
  diagnosisRequests: number; levelCount: Record<Signal, number>; llmTokens: number; ragQueries: number; ragEmpty: number;
  reportCacheHits: number; reportCacheMiss: number; chatQuestions: number; guardrailFail: number;
  redShare: number; redAlarm: boolean; ragEmptyRate: number; coverage: { riskType: RiskType; docs: number }[]; cacheEntries: number;
}

export default function AdminView({ docs }: { docs: PolicyDoc[] }) {
  const [m, setM] = useState<M | null>(null);
  useEffect(() => {
    const load = () => getJSON<M>('/api/admin/metrics').then(setM);
    load(); const t = setInterval(load, 5000); return () => clearInterval(t);
  }, []);
  const total = m ? m.levelCount.GREEN + m.levelCount.YELLOW + m.levelCount.RED : 0;
  return (
    <div className="page">
      <div className="page-head">
        <span className="badge badge-outline" style={{ justifySelf: 'start' }}>내부 운영 화면</span>
        <h1>운영 대시보드</h1>
        <p>목업에서는 개발 서버 메모리의 카운터를 5초마다 읽습니다. 서버를 재시작하면 초기화됩니다.</p>
      </div>

      <section className="card">
        <div className="card-head"><div><h2>서비스 지표</h2><p><Spec ids="F-SYS-06 · F-SYS-07" /></p></div></div>
        {m ? (
          <>
            <div className="stats">
              <div className="stat"><div className="k">진단 요청</div><div className="v">{m.diagnosisRequests}</div></div>
              <div className="stat"><div className="k">C등급(RED) 비율</div><div className="v">{(m.redShare * 100).toFixed(1)}%</div><div className="s">기대치 약 14%</div></div>
              <div className="stat"><div className="k">RAG 빈 결과율</div><div className="v">{(m.ragEmptyRate * 100).toFixed(1)}%</div><div className="s">{m.ragEmpty} / {m.ragQueries}건</div></div>
              <div className="stat"><div className="k">LLM 토큰(추정)</div><div className="v">{m.llmTokens.toLocaleString()}</div><div className="s">Q&A {m.chatQuestions}건</div></div>
              <div className="stat"><div className="k">리포트 캐시</div><div className="v">{m.reportCacheHits} / {m.reportCacheHits + m.reportCacheMiss}</div><div className="s">HIT · 키 {m.cacheEntries}개</div></div>
              <div className="stat"><div className="k">가드레일 실패</div><div className="v">{m.guardrailFail}</div></div>
              <div className="stat"><div className="k">등급 분포</div><div className="v" style={{ fontSize: 15 }}>A {m.levelCount.GREEN} · B {m.levelCount.YELLOW} · C {m.levelCount.RED}</div><div className="s">총 {total}건</div></div>
            </div>
            {m.redAlarm
              ? <p className="notice notice-danger" style={{ marginTop: 12 }}>⚠ C등급 비율이 실제 사전확률(약 14%)에서 10%p 이상 벗어났습니다. 사전확률 보정(F-DIA-04) 적용 여부를 확인하세요.</p>
              : <p className="hint" style={{ marginTop: 10 }}>진단 20건 이상 누적 시 C등급 비율이 14%±10%p를 벗어나면 보정 오류 알람이 뜹니다.</p>}
          </>
        ) : <p className="muted">불러오는 중…</p>}
      </section>

      <section className="card">
        <div className="card-head"><div><h2>원인 유형별 문서 커버리지</h2><p>6개 유형 모두 최소 1건 이상 매칭 문서 필요 · <Spec ids="F-RAG-02" /></p></div></div>
        <div className="row">
          {m?.coverage.map((c) => (
            <span key={c.riskType} className={`badge ${c.docs ? 'badge-GREEN' : 'badge-RED'}`}>{c.docs ? '✓' : '✕'} {RISK_TYPE_META[c.riskType].name} {c.docs}건</span>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="card-head">
          <div><h2>정책자금 문서</h2><p>수기 등록·태깅 (자동 수집은 후속) · <Spec ids="F-RAG-01 · 02 · 05" /></p></div>
          <button className="btn btn-sm" disabled title="목업: 실제 색인 배치(CLI build_index) 미연결">재색인 실행</button>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>제목</th><th>risk_type 태그</th><th>소관기관</th><th>한도</th><th>금리</th><th>신청기간</th><th>URL</th><th>갱신</th></tr></thead>
            <tbody>{docs.map((d) => (
              <tr key={d.docId}>
                <td className="spec-tag">{d.docId}</td><td>{d.title}</td>
                <td>{d.riskTypeTags.map((t) => RISK_TYPE_META[t].name).join(', ')}</td>
                <td>{d.agency}</td>
                {[d.limit, d.rate, d.period].map((v, i) => <td key={i} className={v === '확인 필요' ? 'muted' : ''}>{v === '확인 필요' ? <span className="badge badge-YELLOW">! 확인 필요</span> : v}</td>)}
                <td>{d.url ? 'O' : <span className="badge badge-YELLOW">! 미등록</span>}</td><td className="muted">{d.updatedAt}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <div className="card-head"><div><h2>성능 목표</h2><p>백엔드 연결 후 측정 · <Spec ids="F-SYS-02" /></p></div></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>구간</th><th>목표 (p95)</th><th>엔드포인트</th></tr></thead>
            <tbody>
              <tr><td>상권 조회</td><td>&lt; 500ms</td><td className="spec-tag">GET /api/market/*</td></tr>
              <tr><td>진단 추론</td><td>&lt; 2s</td><td className="spec-tag">POST /api/diagnosis</td></tr>
              <tr><td>정책자금 검색</td><td>&lt; 800ms</td><td className="spec-tag">POST /api/solutions</td></tr>
              <tr><td>LLM 리포트 첫 토큰</td><td>&lt; 3s</td><td className="spec-tag">POST /api/report</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
