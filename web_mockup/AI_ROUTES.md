# AI 기능 경로표

프론트 목업에서 AI가 들어갈 자리와 호출 경로 정리. 지금은 `app/api/` 목업 응답이고, 백엔드가 같은 경로를 만들면 `BACKEND_URL` 설정으로 넘어감 (`next.config.mjs`).

요청·응답 타입은 `lib/types.ts` 기준.

| # | 기능 | 사용자 진입 경로 | 페이지 | API | 로그인 |
|---|---|---|---|---|---|
| 1 | AI 진단 리포트 | 사업장 진단 → 결과 → "리포트 생성하기" | `/diagnosis/[id]` | `POST /api/report` (스트리밍) | - |
| 2 | 서비스 챗봇 | 상단 메뉴 "챗봇 상담" / 진단 결과 → "챗봇에게 물어보기" | `/chatbot`, `/chatbot?diagnosis=ID` | `POST /api/chatbot` | - |
| 3 | 고객 분석 AI | `/admin` 로그인 → "고객 분석 AI" | `/admin/insights` | `POST /api/admin/insights` | 관리자 |

상권 지도의 지표 해설은 이미 있는 통계를 문장으로 바꾸는 것뿐이라 AI 없이 화면에서 계산함 (`/market` 지표 요약).

## 1. AI 진단 리포트 `POST /api/report`

- 요청: `{ diagnosisId: string }`
- 응답: 마크다운 텍스트 스트리밍
- 근거: 진단 결과 + 추천 정책 문서만 사용 (F-LLM-01·02)

## 2. 서비스 챗봇 `POST /api/chatbot`

- 요청 `ChatbotRequest`: `{ message: string, diagnosisId?: string, history?: { role, text }[] }` (history 최대 10개, message 500자 이내)
- 응답 `ChatbotResponse`: `{ answer: string, sources: { docId, title }[], links: { label, href }[], remaining?: number }`
- `diagnosisId` 없음: 일반 상담 (정책자금, 진단·상권 화면 안내)
- `diagnosisId` 있음: 그 진단 결과 기준 답변. 진단 1건당 질문 5개 제한, 초과 시 429, `remaining`에 남은 수
- `sources`: 답변 근거 정책 문서, `links`: 이어서 갈 화면

## 3. 고객 분석 AI `POST /api/admin/insights`

- 요청 `InsightRequest`: `{ question: string }`
- 응답 `InsightResponse`: `{ answer: string, stats: { total, byLevel, byRiskType, topGu, topService }, generatedAt: string }`
- 관리자 쿠키 없으면 401 (`middleware.ts`)
- 목업은 서버 메모리의 진단 기록을 집계함. 실제는 diagnosis 테이블 집계 + LLM 요약

## 백엔드 연결

```powershell
$env:BACKEND_URL="http://localhost:8000"; npm run dev
```

`/api/*` 요청이 FastAPI로 넘어감. 관리자 API는 Next 미들웨어에서 로그인 확인 후 넘김.
