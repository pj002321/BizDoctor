# BizDoctor 웹 목업 (Next.js)

기능정의서(BizDoctor_기능정의서) P0~P2 전 기능을 화면으로 옮긴 **로컬 목업**.
상권 데이터는 실제 CSV 산출물에서 일부 추출한 값이고, 진단·리포트·Q&A는 실제 모델/LLM 대신 같은 입출력 형태의 목업 로직.

## 실행 (Windows)

1. Node.js 20 이상 설치 (https://nodejs.org → LTS)
2. 터미널에서

```powershell
cd web_mockup
npm install
npm run dev
```

3. 브라우저에서 http://localhost:3000

## 화면 ↔ 기능정의서

| 경로 | 화면 | 기능 ID |
|---|---|---|
| `/` | 홈 — 상권 신호등 / 사업장 진단 진입 분리 | F-SYS-01 |
| `/market` | 자치구 지도 → 행정동 성적표 → 업종 상세, 공통 필터, AI 해설 | F-MAP-01·02·03·06, F-LLM-04 |
| `/market/trends` | 분기별 산업 추이 (2024 Q1 역전 주석) | F-MAP-04 |
| `/market/industries` | 업종별 폐업률 순위 | F-MAP-05 |
| `/diagnosis` | 진단 입력 (매출 → 지수 정규화, 금액 미저장) | F-DIA-01, F-SYS-05 |
| `/diagnosis/[id]` | 진단 등급·보정확률·추정원인·점수·상권 위치·지원사업·AI 리포트·Q&A·공유 | F-DIA-03~08, F-RAG-04, F-LLM-01·02·03·05, F-SYS-07·08 |
| `/share/[token]` | 공유 링크 열람 (매출 관련 수치 제외) | F-DIA-08 |
| `/methodology` | 계산 방법과 모델 한계 | F-SYS-08 |
| `/admin` | 운영 지표·문서 커버리지·정책문서·성능 목표 | F-SYS-06, F-RAG-01·02·05, F-SYS-02 |

모든 화면 우측 상단의 회색 코드(`F-MAP-01` 등)가 기능 ID.

## API (목업 route handler = 백엔드 계약 초안)

기능정의서의 API 경로 그대로 `app/api/` 아래에 구현. 응답 타입은 **`lib/types.ts`** 에 정리 → 백엔드 Pydantic 스키마 기준으로 사용.

| 메서드 | 경로 | 기능 |
|---|---|---|
| GET | `/api/market/regions` | F-MAP-01 (쿼리: qFrom, qTo, industry, service, minStores) |
| GET | `/api/market/regions/{gu}/dongs` | F-MAP-02 |
| GET | `/api/market/cells?dongCode=&service=` | F-MAP-03 (service 생략 시 업종 목록) |
| GET | `/api/market/trends` | F-MAP-04 |
| GET | `/api/market/industries?sort=avg\|real&top=N` | F-MAP-05 |
| POST | `/api/diagnosis` | F-DIA-01~06 → 신호 JSON (F-RAG-04) |
| GET | `/api/diagnosis/context` | F-DIA-07 |
| GET | `/api/diagnosis/{id}` (`?token=` 공유) | F-DIA-08 |
| POST | `/api/solutions` | F-RAG-03 |
| POST | `/api/report` (스트리밍) | F-LLM-01·02 |
| POST | `/api/chat` | F-LLM-03 |
| POST | `/api/explain` | F-LLM-04 |
| GET | `/api/admin/metrics` | F-SYS-06 |
| GET | `/api/meta` | 폼·필터 선택지 (정의서 외 보조) |

### 실제 백엔드로 전환

FastAPI가 같은 경로를 제공하면, 환경변수만 지정해 실행 → `/api/*` 요청이 백엔드로 넘어감 (화면 코드 수정 불필요).

```powershell
$env:BACKEND_URL="http://localhost:8000"; npm run dev
```

## 데이터

- `data/*.json` — `scripts/build_data.py` 로 프로젝트 루트의 CSV에서 추출 (약 13MB)
- 자치구 집계 산식은 `tableau_region_summary.csv` 와 동일 (최소 점포수 0, 전체 기간일 때 25개 구 × 8개 산업 값 일치 확인)
- 행정동 성적표 산식은 `risk_weights_by_region_industry.csv` 와 동일 (관측 8건·연점포수 100 기준)
- 재생성: 프로젝트 루트에서 `.\.venv\Scripts\python.exe web_mockup\scripts\build_data.py`

## 목업 한계

- 진단 등급·원인 유형 확률은 **규칙 기반 대체 로직** (risk_model.keras 미연결)
- AI 리포트·Q&A·해설은 템플릿 (LLM 미연결). 스트리밍·수치 대조 가드레일·캐시 흐름만 재현
- 진단 결과·지표는 개발 서버 메모리에 저장 → 서버 재시작 시 초기화
- 정책 문서 URL·일부 한도/금리는 원문에 없어 '확인 필요'로 표기
