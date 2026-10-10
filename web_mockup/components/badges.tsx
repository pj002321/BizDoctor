import { DIAG_GRADE, MARKET_SIGNAL } from '@/lib/risk';
import type { Signal } from '@/lib/types';

/** 상권 신호 — 색 + 아이콘 + 라벨 병기 (F-SYS-04) */
export function SignalBadge({ signal }: { signal: Signal | null }) {
  if (!signal) return <span className="badge badge-NA" title="관측 8건 미만 또는 연점포수 100 미만">◌ 표본부족</span>;
  const m = MARKET_SIGNAL[signal];
  return <span className={`badge badge-${signal}`}><span aria-hidden>{m.icon}</span>{m.label}</span>;
}

/** 사업장 진단 등급 — '신호등' 명칭 사용 안 함 (F-SYS-01) */
export function GradeBadge({ level }: { level: Signal }) {
  const g = DIAG_GRADE[level];
  return <span className={`badge badge-${level}`}><span aria-hidden>{g.icon}</span>{g.grade} · {g.label}</span>;
}

export function ScopeChip({ scope }: { scope: 'market' | 'diag' }) {
  return scope === 'market'
    ? <span className="chip-scope scope-market">상권 단위 · 실제 통계</span>
    : <span className="chip-scope scope-diag">사업장 단위 · 모델 추정</span>;
}

/** 기능정의서 ID 표시 (목업 리뷰용) */
export function Spec({ ids }: { ids: string }) {
  return <span className="spec-tag">{ids}</span>;
}

export function SmallSampleBadge() {
  return <span className="badge badge-NA" title="점포수 5개 이하: 폐업률이 0/33/67%처럼 계단값으로 튐">표본 적음</span>;
}
