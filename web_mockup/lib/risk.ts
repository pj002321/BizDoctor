import type { RiskType, Signal } from './types';

/** 상권 신호등 색 기준 (F-MAP-01): 위험가중치 0.60 이하 GREEN / 0.60~0.85 YELLOW / 0.85 초과 RED */
export const MAP_THRESHOLDS = { green: 0.6, red: 0.85 };

export function signalOf(w: number, t = MAP_THRESHOLDS): Signal {
  if (w > t.red) return 'RED';
  if (w > t.green) return 'YELLOW';
  return 'GREEN';
}

/**
 * F-SYS-01: '신호등'은 상권 단위에만, 사업장은 '진단 등급'.
 * 색은 같은 팔레트를 쓰되 라벨·아이콘을 분리해 혼동 방지. (F-SYS-04: 색 단독 전달 금지)
 */
export const MARKET_SIGNAL: Record<Signal, { label: string; icon: string; desc: string }> = {
  GREEN: { label: '양호', icon: '●', desc: '위험가중치 0.60 이하' },
  YELLOW: { label: '주의', icon: '▲', desc: '0.60 초과 ~ 0.85 이하' },
  RED: { label: '위험', icon: '■', desc: '0.85 초과' },
};

export const DIAG_GRADE: Record<Signal, { label: string; grade: string; icon: string }> = {
  GREEN: { label: '안정', grade: 'A', icon: '✓' },
  YELLOW: { label: '관찰 필요', grade: 'B', icon: '!' },
  RED: { label: '위험', grade: 'C', icon: '✕' },
};

export const RISK_TYPES: RiskType[] = ['정상_유지형', '단기_매출_정체형', '원가_상승_부담형', '매출_폭락형', '고금리_과다채무형', '상권_침체_붕괴형'];

export const RISK_TYPE_META: Record<RiskType, { level: Signal; name: string; color: string; message: string; recall: number | null }> = {
  정상_유지형: { level: 'GREEN', name: '정상 유지형', color: '#1F9D57', message: '건전하게 운영되고 있습니다', recall: null },
  단기_매출_정체형: { level: 'YELLOW', name: '단기 매출 정체형', color: '#B7791F', message: '자금 흐름 모니터링이 필요합니다', recall: null },
  원가_상승_부담형: { level: 'YELLOW', name: '원가 상승 부담형', color: '#B7791F', message: '원가 부담이 커지고 있습니다', recall: 0 },
  매출_폭락형: { level: 'RED', name: '매출 폭락형', color: '#C53030', message: '3개월 내 심각한 자금난 발생 위험', recall: 0.012 },
  고금리_과다채무형: { level: 'RED', name: '고금리 과다채무형', color: '#C53030', message: '대출 상환 부담이 위험 수준입니다', recall: null },
  상권_침체_붕괴형: { level: 'RED', name: '상권 침체 붕괴형', color: '#C53030', message: '상권 침체로 폐업 위험이 높습니다', recall: 0 },
};

/** recall: 기능정의서에 명시된 값만 기재, 미기재는 null */
/** 모델 현재 성능 (기능정의서 F-DIA-03 / F-SYS-08 기재 값) */
export const MODEL_PERF = { accuracy: 0.838, redRecall: 0.933, yellowRecall: 0.339 };

/** 사전확률 보정 (F-DIA-04): 학습 RED 비중 30% → 실제 서울 약 14% */
export const BASE_RED_RATE = 0.3;
export const REAL_RED_RATE = 0.14;

export const fmtPct = (v: number | null | undefined, d = 2) => (v == null ? '–' : `${v.toFixed(d)}%`);
export const fmtNum = (v: number | null | undefined) => (v == null ? '–' : v.toLocaleString('ko-KR'));
