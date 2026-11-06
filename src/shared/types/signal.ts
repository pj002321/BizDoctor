/**
 * 사업장 진단 결과 계약(F-RAG-04). ai-service 의 build_signal 이 만드는 JSON 과 같은 모양이다.
 * 진단(features/diagnosis)이 만들고 AI 리포트(features/report)가 읽는다 — 그래서 shared 에 둔다.
 * 검색 점수는 계약에 넣지 않는다(AGENTS.md).
 */

export type RiskLevel = "GREEN" | "YELLOW" | "RED";

export type RiskType =
  | "정상_유지형"
  | "단기_매출_정체형"
  | "원가_상승_부담형"
  | "매출_폭락형"
  | "고금리_과다채무형"
  | "상권_침체_붕괴형";

export const RISK_TYPE_LEVEL: Record<RiskType, RiskLevel> = {
  정상_유지형: "GREEN",
  단기_매출_정체형: "YELLOW",
  원가_상승_부담형: "YELLOW",
  매출_폭락형: "RED",
  고금리_과다채무형: "RED",
  상권_침체_붕괴형: "RED",
};

/** 진단 등급 표기. 상권 "신호등"과 섞이지 않게 글자 등급과 이름을 따로 쓴다(F-SYS-01). */
export const GRADE: Record<RiskLevel, { letter: string; label: string }> = {
  GREEN: { letter: "A", label: "안정" },
  YELLOW: { letter: "B", label: "관찰 필요" },
  RED: { letter: "C", label: "위험" },
};

export interface Solution {
  title: string;
  agency: string;
  summary: string;
  target: string;
  limit: string;
  rate: string;
  period: string;
  source_doc_id: string;
}

export interface Signal {
  risk_level: RiskLevel;
  risk_type: RiskType;
  risk_type_confidence: number;
  /** 0~100. 높을수록 위험 */
  score: number;
  visual_theme: "green" | "yellow" | "red";
  solutions: Solution[];

  /* 화면용 보조 값 (목업). 실서비스에서는 진단 응답의 같은 이름 필드로 온다. */
  level_probs: Record<RiskLevel, number>;
  type_probs: Record<RiskType, number>;
  low_confidence: boolean;
  /** 1개월차 = 100 지수. 실금액은 어디에도 남기지 않는다(F-SYS-05). */
  sales_index: [number, number, number];
  place: { gu: string; dong: string; service: string; industry: string };
  /** 같은 업종 안에서 이 행정동 폐업률의 위치(0~1, 높을수록 폐업이 잦음) */
  percentile: number;
  close_rate: number;
  as_of: string;
}

/** 진단 화면이 결과를 남기고 리포트 화면이 읽는 sessionStorage 키. 매출 지수만 담긴다. */
export const SIGNAL_STORAGE_KEY = "bizdoctor:signal";
