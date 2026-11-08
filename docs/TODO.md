# 확장 기능 작업 목록

원본: `docs/BizDoctor 확장 기능 명세서.docx` (2026-10-30).
RAG 1~9스텝은 `EMBEDDING_TODO.md` 에서 관리한다. 거기 남은 10~13스텝은 아래 단계로 흡수한다.

| EMBEDDING_TODO | 여기서 |
|---|---|
| 10. Tool Calling + LangGraph | 2단계 (기능 2) |
| 11. API 연결 | 2단계 끝 — 그래프를 엔드포인트에 붙인다 |
| 12. 평가 · 관측 | 1단계 (기능 1) + 3단계 (기능 4, 요청 로그를 Langfuse 로 대체) |
| 13. 정기 수집 | 4단계 (기능 7) |

순서는 고정이다. 각 단계의 **관문**을 통과해야 다음으로 넘어간다 — 뒤 단계는 모두 1단계 수치로 효과를 증명한다.

---

## 0. 선행 — 1단계를 막는 것

- [ ] 기업마당 API 키(`crtfcKey`) 발급 신청 — 공고 20건 확보가 여기 달려 있다
- [ ] 수동 6건 원문 대조 (2차 출처 섞임, `EMBEDDING_TODO.md` 2스텝)
- [ ] 공고 20건 이상 · 유형별 3건+ · 긴 공고 1~2건 (키 전이면 수동 입력으로 채운다)

## 1단계. 평가 기준선 (기능 1)

관문: **hit@3 기준선 확정**

- [ ] `ai-service/eval/golden.jsonl` 형식 확정 — `question, risk_type, gold_doc_ids, gold_facts, type`
- [ ] 질문 50개 이상 직접 작성, 5유형(위기 유형 · 조건 · 수치 · 마감 함정 · 범위 밖) 각 5개 이상
  - LLM 변형은 검토 후에만 넣는다
- [ ] 검색 지표: hit@3 · MRR · 마감 공고 노출률(0 이 정답)
- [ ] 생성 지표: 근거 충실도 · 수치 일치율 · 거절 정확도
- [ ] 운영 지표: 요청당 토큰 · p50/p95 지연 · 재생성·폴백 비율
- [ ] 검색 설정 분리: 벡터 단독 · BM25 단독 · RRF · RRF + 태그 우선 (`retrieve.py` 인터페이스는 유지)
- [ ] `python -m eval.run --config rrf` 한 번으로 실험 표 한 줄이 채워짐
- [ ] 실험 표 4줄 채움 → 리랭커 추가 여부를 이 표로 결정
- [ ] CI: hit@3 가 기준선 아래면 실패 (`.github/` 없음 — 여기서 처음 만든다)

## 2단계. Corrective RAG (기능 2 · 6)

관문: **마감 함정 · 범위 밖 질문 환각 0건**

### 리포트 그래프 (`app/graph/`)
- [ ] 상태 정의 — `attempts` 로 재시도 상한
- [ ] `retrieve` — 기존 `retrieve.py` 호출
- [ ] `grade_docs` — 처음엔 규칙(태그 일치 + 점수 임계값). 1단계 지표가 나쁘면 LLM 판정으로
- [ ] `rewrite_query` — 태그 필터 해제 + 질의 확장, 그래도 0건이면 "해당 지원사업 없음"
- [ ] `generate` → `guardrail` → `cross_check` — 실패 시 위반 목록을 `feedback` 으로 1회 재생성 (`report.py` · `guardrail.py` · `verify.py` 재사용)
- [ ] `fallback` — 템플릿 리포트
- [ ] 실제 OpenAI · Claude 호출 확인 (8·9스텝에서 미확인)

### 챗봇 그래프
- [ ] `app/tools/` 에 `search_policy` · `get_market_stats` — 3단계 MCP 와 같은 함수를 쓴다
- [ ] Tool Calling 으로 도구 선택, 답변은 검증 후 출력

### API (EMBEDDING_TODO 11)
- [ ] FastAPI 엔드포인트 · `X-Service-Token` · `web_mockup/AI_ROUTES.md` 계약 · 목업 연동

### 생성 모델 벤치마크 (기능 6)
- [ ] 검색 결과 고정, 생성 모델 2~3개로 충실도 · 지연 · 비용 비교 — `eval/` 스크립트에서만 모델을 바꾼다
- [ ] 리포트용 · 챗봇용 모델 각각 선정. 생성과 검증은 제공사를 다르게

### 확인
- [ ] 교차 검증 도입 전후 근거 충실도 수치

## 3단계. 도구 · 관측 (기능 3 · 4)

관문: **리포트 1건의 노드별 지연이 트레이스 하나로 보임**

### MCP 서버 (기능 3)
- [ ] `ai-service/app/mcp/server.py` — Python MCP SDK, 도구 본체는 `retrieve.py` · `market_service.py` 그대로
- [ ] `search_policy(질의, risk_type?, top_k)` — 마감 제외 동일 적용, 조각 + doc_id + url
- [ ] `get_market_stats(자치구, 행정동, 업종)` — 폐업률 · 개업률 · 추이, 점포 5 이하면 "표본 적음"
- [ ] `diagnose` 는 노출하지 않음 (매출 입력 = 개인정보). 쓰기 도구 없음
- [ ] 로컬 stdio, 배포 Streamable HTTP + 서비스 토큰
- [ ] pytest 도구 응답 계약 테스트 · MCP Inspector 스키마 검증
- [ ] Claude Desktop: "강남구 카페 폐업률과 맞는 지원사업" 이 도구 2개 호출로 답됨

### Langfuse (기능 4)
- [ ] Docker 셀프호스팅
- [ ] LangGraph 콜백 핸들러로 노드별 span
- [ ] trace: 진단 등급·유형, 최종 결과(통과/재생성/폴백) — 매출 지수 · 행정동 등 고유값 **제외**
- [ ] generation: 모델명 · 토큰 · 비용, 프롬프트는 마스킹 후 저장
- [ ] score: 교차 검증 충실도 · 사용자 좋아요/싫어요
- [ ] 대시보드: 노드별 p50/p95 · 요청당 비용 · 재생성·폴백 비율 · 검색 0건 비율
- [ ] 골든셋 평가를 Langfuse dataset run 으로 업로드
- [ ] `/admin` 운영 지표가 이 값을 읽게
- [ ] 트레이스에 사업장 고유값이 없는지 검사하는 테스트
- [ ] 2단계 "노드별 통과 · 재시도 · 폴백 횟수" 가 대시보드에 보임

## 4단계. 수집 · 배포 (기능 7 · 8)

관문: **CI 회귀 검사 통과**

### 수집 파이프라인 (기능 7, EMBEDDING_TODO 13 설계 유지)
- [ ] ⚠ 먼저 확인: 기업마당 `printFlpthNm` 으로 HWP 공고 텍스트를 얻을 수 있는지
- [ ] ⚠ 먼저 확인: 상권분석서비스 새 형식(표준단위구역, 2021년 이후만)과 prep 단계 호환
- [ ] 수집: EventBridge 매주 월 → 기업마당 · K-Startup API → 원문 S3
- [ ] 파싱: SQS → 항목 단위 추출 → `PolicyDoc` Pydantic 검증
- [ ] 검토: `policy_docs.json` 변경 PR, 사람이 숫자 · 태그 확인 후 머지
- [ ] 적재: 머지 이벤트 → `load_docs` · chunk · `build_index`, 변경분만
- [ ] 멱등 키 = 공고 ID + 내용 해시 (재실행 시 변경 0건 유지)
- [ ] 3회 실패 → DLQ, 관리자 화면 표시
- [ ] 안전장치: `last_seen_at` 30일 유예 삭제 · 수집 실패나 직전 대비 50% 미만이면 삭제 안 함

### 배포 (기능 8)
- [ ] Dockerfile: web · ai-service
- [ ] docker-compose: web · ai-service · Langfuse 한 번에
- [ ] GitHub Actions: pytest + vitest + 골든셋 회귀 → ECR 푸시 → ECS 배포
- [ ] VPC: Next.js 만 퍼블릭(ALB 또는 Vercel), ai-service 는 프라이빗 서브넷 + 보안 그룹으로 Next.js 에서만
- [ ] S3: `risk_model.keras` 버전 관리 · 공고 원문
- [ ] Secrets Manager: API 키 · 서비스 토큰
- [ ] (선택) Terraform 으로 VPC · 보안 그룹

## 5단계. 검증 증류 (기능 5)

관문: **틀린 주장 재현율 비교** — Claude 보다 낮으면 단독 교체 없이 단계형만

- [ ] 2단계 실행마다 `(근거, 주장, supported, reason)` 저장, 고유값 마스킹
- [ ] 음성 표본 부족하면 근거 숫자 · 조건을 바꾼 "틀린 주장" 합성
- [ ] 골든셋 출처 표본은 학습 제외, 평가 전용 (누수 방지)
- [ ] 데이터 카드: 표본 수 · 양성/음성 비율
- [ ] 한국어 소형 오픈 모델 2~3개를 프롬프트만으로 비교해 베이스 선정
- [ ] PEFT LoRA(필요하면 QLoRA), 출력은 기존 Verdict JSON 스키마
- [ ] vLLM OpenAI 호환 서버, `verify.py` 는 설정값 하나로 Claude ↔ 소형 모델 전환
- [ ] 단계형: 소형 모델 저확신 주장만 Claude 로
- [ ] 비교 표 4줄(Claude · 프롬프트만 · LoRA · 단계형) × 재현율 · 정밀도 · p95 · 1,000건당 비용
- [ ] 학습 환경(Colab / 클라우드 GPU) 명시

---

## 미정

- 공고 20건 확보 시점 — 기업마당 API 키 발급에 달림
- 파인튜닝 GPU — Colab 또는 클라우드 GPU
- Supabase 유지 또는 RDS 전환 — 비용 보고 결정
