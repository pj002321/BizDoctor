import Link from 'next/link';
import { ScopeChip, Spec } from '@/components/badges';

export default function ServiceHome() {
  return (
    <div className="page">
      <section className="hero">
        <span className="badge badge-brand" style={{ justifySelf: 'start' }}>서울 소상공인 폐업 위험 조기 경보</span>
        <h1>우리 동네 상권은 어떤지,<br />내 가게는 괜찮은지</h1>
        <p className="muted" style={{ maxWidth: 620 }}>
          실제 상권 통계로 본 <b>상권 신호등</b>과, 내 매출로 계산하는 <b>사업장 진단 등급</b>을 따로 보여드립니다.
          진단 결과에 맞는 2026년 정책자금도 함께 찾아드려요.
        </p>
      </section>

      {/* F-SYS-01: 두 결과를 명칭·색 범례·URL로 분리 */}
      <div className="grid-2" style={{ gridTemplateColumns: undefined }}>
        <Link href="/market" className="entry">
          <div className="row between"><ScopeChip scope="market" /><Spec ids="F-MAP-01~06" /></div>
          <div className="lights" aria-hidden><i style={{ background: 'var(--green-fill)' }} /><i style={{ background: 'var(--yellow-fill)' }} /><i style={{ background: 'var(--red-fill)' }} /></div>
          <h2>상권 신호등</h2>
          <p className="muted small">서울 25개 자치구 · 425개 행정동 · 100개 업종의 11개 분기 폐업 통계를 지도와 성적표로 확인합니다.</p>
          <span className="btn btn-sm" style={{ justifySelf: 'start' }}>지도 보기 →</span>
        </Link>
        <Link href="/diagnosis" className="entry">
          <div className="row between"><ScopeChip scope="diag" /><Spec ids="F-DIA · F-RAG · F-LLM" /></div>
          <div className="row" aria-hidden style={{ gap: 6 }}>
            <span className="badge badge-GREEN">✓ A</span><span className="badge badge-YELLOW">! B</span><span className="badge badge-RED">✕ C</span>
          </div>
          <h2>사업장 진단</h2>
          <p className="muted small">행정동·업종·최근 3개월 매출을 입력하면 진단 등급, 추정 원인, 맞춤 지원사업과 AI 리포트를 받아볼 수 있습니다.</p>
          <span className="btn btn-primary btn-sm" style={{ justifySelf: 'start' }}>진단 시작 →</span>
        </Link>
      </div>

      <div className="grid-3">
        <div className="card"><h3>매출 금액은 저장하지 않아요</h3><p className="muted small" style={{ marginTop: 4 }}>입력한 금액은 1개월차=100 지수로 바꿔 계산에만 쓰고 바로 버립니다. <Spec ids="F-SYS-05" /></p></div>
        <div className="card"><h3>추정은 추정이라고 말해요</h3><p className="muted small" style={{ marginTop: 4 }}>원인 유형은 확률과 함께 &lsquo;추정 원인&rsquo;으로만 표기하고 모델 한계를 공개합니다. <Spec ids="F-SYS-08" /></p></div>
        <div className="card"><h3>근거 있는 리포트</h3><p className="muted small" style={{ marginTop: 4 }}>AI 리포트의 모든 수치·사업명은 진단 결과와 공고 문서에 있는 값만 씁니다. <Spec ids="F-LLM-02" /></p></div>
      </div>
    </div>
  );
}
