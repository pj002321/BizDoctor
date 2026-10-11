/**
 * API 계약(Contract) 타입 — 프론트 ↔ 백엔드 합의용 스키마 초안
 * 기능정의서의 API 컬럼과 1:1 대응. 백엔드(Pydantic) 스키마는 이 구조를 기준으로 맞추면 됨.
 * 필드명은 프론트 관례상 camelCase, 원본 CSV 컬럼명은 주석에 병기.
 */

export type Signal = 'GREEN' | 'YELLOW' | 'RED';

export type RiskType =
  | '정상_유지형'
  | '단기_매출_정체형'
  | '원가_상승_부담형'
  | '매출_폭락형'
  | '고금리_과다채무형'
  | '상권_침체_붕괴형';

/** 공통 필터 (F-MAP-06) — 모든 /api/market/* 에 쿼리 파라미터로 전달 */
export interface MarketFilter {
  qFrom?: string;      // 예: '2023 Q1'
  qTo?: string;        // 예: '2025 Q3'
  gu?: string;         // 자치구
  industry?: string;   // 산업대분류 (KOSIS_산업1)
  service?: string;    // 서비스_업종_코드 (예: CS100001)
  minStores?: number;  // 최소 점포수, 기본 5
}

/** GET /api/market/regions (F-MAP-01) */
export interface RegionRisk {
  gu: string;
  signal: Signal;
  riskWeight: number;      // 위험가중치 = 폐업률_업종내_percentile 평균
  realCloseRate: number;   // 실질폐업률(가중) = Σ폐업점포 / Σ점포 × 100  ← 기본 표기
  avgCloseRate: number;    // 평균폐업률 (보조 표기)
  avgOpenRate: number;
  stores: number;          // Σ점포수 (분기 합)
  obs: number;             // 관측수 (행 수)
}
export interface RegionsResponse {
  filter: MarketFilter;
  thresholds: { green: number; red: number };
  regions: RegionRisk[];
}

/** GET /api/market/regions/{gu}/dongs (F-MAP-02) */
export interface DongRisk {
  dongCode: string;
  dong: string;
  industry: string;
  sufficient: boolean;     // 관측 8건 이상 & 연점포수 100 이상
  signal: Signal | null;   // 표본부족이면 null
  riskWeight: number | null;
  avgCloseRate: number | null;
  closeOpenGap: number | null; // 폐업개업격차
  obsQuarters: number;
  storeYears: number;      // 연점포수
}
export interface DongsResponse { gu: string; filter: MarketFilter; dongs: DongRisk[] }

/** GET /api/market/cells?dongCode=&service= (F-MAP-03) */
export interface CellPoint {
  quarter: string;
  stores: number | null;
  closeRate: number | null;
  openRate: number | null;
  closeOpenGap: number | null;
  percentile: number | null;   // 폐업률_업종내_percentile
  franchiseShare: number | null; // 프랜차이즈_비중
  smallSample: boolean;        // 점포수 5개 이하 → '표본 적음' 배지
}
export interface CellResponse {
  dongCode: string; dong: string; gu: string;
  service: string; serviceName: string; industry: string;
  series: CellPoint[];
}

/** GET /api/market/trends (F-MAP-04) */
export interface TrendPoint { quarter: string; industry: string; avgCloseRate: number; avgOpenRate: number; realCloseRate: number }
export interface TrendsResponse {
  series: TrendPoint[];
  annotations: { quarter: string; label: string }[];
}

/** GET /api/market/industries (F-MAP-05) */
export interface IndustryRank { rank: number; name: string; industry: string; avgCloseRate: number; realCloseRate: number; obs: number; stores: number }

/** POST /api/diagnosis 요청 (F-DIA-01) — 매출 실금액은 서버 미저장 (F-SYS-05) */
export interface DiagnosisRequest {
  dongCode: string;
  service: string;
  revenue: [number, number, number]; // 최근 3개월 월매출(원) — 요청 처리 중에만 사용
  prevRevenue?: [number, number, number]; // 선택: 그 이전 3개월 (있으면 표준 score 산식)
}

/** 신호 JSON 계약 (F-RAG-04) — POST /api/diagnosis 응답 본문 */
export interface Solution {
  solutionId: string;     // source_doc_id
  title: string;
  agency: string;
  summary: string;
  limit: string;
  rate: string;
  url: string;
  actionType: 'APPLY_NOW' | 'LINK_GUIDE';
  actionLabel: string;
}
export interface SignalResponse {
  diagnosisId: string;
  shareToken: string;
  createdAt: string;
  expiresAt: string;           // 비로그인 24시간 (F-DIA-08)
  input: { dongCode: string; dong: string; gu: string; service: string; serviceName: string; industry: string };
  revenueIndex: [number, number, number];   // 1개월차=100 지수 (F-DIA-01) — 저장 대상
  riskLevel: Signal;                        // F-DIA-03
  levelProbs: Record<Signal, number>;       // 사전확률 보정 후 (F-DIA-04)
  priorCorrected: true;
  riskType: RiskType;                       // F-DIA-05 — '추정 원인'
  typeProbs: Record<RiskType, number>;
  lowConfidence: boolean;                   // YELLOW 등 재현율 낮은 경우
  score: number;                            // F-DIA-06 (0~100)
  scoreMethod: 'six_month_drop' | 'three_month_slope';
  context: DiagnosisContext;                // F-DIA-07
  visualTheme: { bgColor: string; animation: 'soft_glow' | 'blink_caution' | 'pulse_warning'; impactMessage: string };
  solutions: Solution[];                    // F-RAG-03/04
  features: { percentile: number; closeRate: number; openRate: number; franchiseShare: number; kosisIndustry: string; fallback: boolean; asOf: string };
}

/** GET /api/diagnosis/context (F-DIA-07) */
export interface DiagnosisContext {
  percentile: number;       // 0~1
  topPercent: number;       // 상위 n%
  hist: number[];           // 같은 업종·분기 분포 (20구간)
  sentence: string;
  peers: number;
}

/** GET /api/diagnosis/{id}?token= (F-DIA-08) — 공유 링크 열람 시 매출 관련 수치 제외 */
export type SharedDiagnosis = Pick<SignalResponse, 'diagnosisId' | 'createdAt' | 'expiresAt' | 'input' | 'riskLevel' | 'riskType' | 'typeProbs' | 'levelProbs' | 'solutions'> & { shared: true };

/** POST /api/chatbot — 챗봇 상담 (진단 없이 누구나) */
export interface ChatbotRequest {
  message: string;
  history?: { role: 'user' | 'assistant'; text: string }[]; // 직전 대화 (최대 10개)
}
export interface ChatbotResponse {
  answer: string;
  sources: { docId: string; title: string }[]; // 답변 근거 문서
  links: { label: string; href: string }[];     // 이어서 갈 수 있는 화면
}

/** POST /api/admin/insights — 관리자 고객 분석 AI */
export interface InsightRequest { question: string }
export interface InsightResponse {
  answer: string;
  stats: {
    total: number;
    byLevel: Record<Signal, number>;
    byRiskType: { riskType: RiskType; count: number }[];
    topGu: { gu: string; count: number }[];
    topService: { service: string; count: number }[];
  };
  generatedAt: string;
}
