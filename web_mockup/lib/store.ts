/**
 * 목업용 인메모리 저장소 — 개발 서버를 재시작하면 사라짐.
 * 실제: diagnosis 테이블(F-DIA-08), 로그·지표(F-SYS-06), 캐시(F-SYS-07), 대화 이력(F-LLM-03).
 * 저장 대상은 정규화 지수뿐이며 매출 실금액은 애초에 이 객체에 들어오지 않음 (F-SYS-05).
 */
import type { Signal, SignalResponse } from './types';

interface Metrics {
  diagnosisRequests: number;
  levelCount: Record<Signal, number>;
  llmTokens: number;
  ragQueries: number;
  ragEmpty: number;
  reportCacheHits: number;
  reportCacheMiss: number;
  chatQuestions: number;
  guardrailFail: number;
}
interface Store {
  diagnoses: Map<string, SignalResponse>;
  chats: Map<string, { role: 'user' | 'assistant'; text: string }[]>;
  reportCache: Map<string, string>;
  metrics: Metrics;
}

const g = globalThis as unknown as { __bizdoctor?: Store };
export const store: Store = (g.__bizdoctor ??= {
  diagnoses: new Map(),
  chats: new Map(),
  reportCache: new Map(),
  metrics: {
    diagnosisRequests: 0, levelCount: { GREEN: 0, YELLOW: 0, RED: 0 }, llmTokens: 0,
    ragQueries: 0, ragEmpty: 0, reportCacheHits: 0, reportCacheMiss: 0, chatQuestions: 0, guardrailFail: 0,
  },
});

export const CHAT_LIMIT = 5; // F-LLM-03 세션당 질문 수 제한

export function saveDiagnosis(d: SignalResponse) {
  store.diagnoses.set(d.diagnosisId, d);
  store.metrics.diagnosisRequests++;
  store.metrics.levelCount[d.riskLevel]++;
  store.metrics.ragQueries++;
  if (d.solutions.length === 0) store.metrics.ragEmpty++;
}

export function getDiagnosis(id: string) {
  const d = store.diagnoses.get(id);
  if (!d) return null;
  if (new Date(d.expiresAt).getTime() < Date.now()) { store.diagnoses.delete(id); return null; }
  return d;
}
