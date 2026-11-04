# RAG 파이프라인 작업 목록 (ai-service)

목표: 실무에 바로 적용할 수 있는 구조. 데모가 아니라 운영에서 터지는 지점을 처음부터 막는다.
코드는 직접 작성하고, 스텝은 하나씩 진행한다.

## 확정 스펙

| 영역 | 결정 |
|---|---|
| 문서 원천 | `ai-service/data/raw/policy_docs.json` 이 검토를 거친 원본. 매주 수집기가 이 파일을 고치는 PR 을 열고, 사람이 숫자·태그를 확인해 머지한다 (13스텝) |
| 저장소 | Supabase Postgres + pgvector (DB 하나) |
| 스키마 | `policy_doc`(문서 · 1) / `policy_chunk`(조각 · N) |
| 청킹 | 공고 항목 단위 → 길면 토큰으로 한 번 더. 조각 앞에 `[제도명 · 항목명]` |
| 임베딩 | OpenAI `text-embedding-3-small` (1536). 조각마다 `embedding_model` 기록 |
| 검색 | ① 마감 제외 → ② risk_type 태그 우선 → ③ 벡터 + 키워드 RRF → ④ 문서당 1개 |
| 생성 | OpenAI. 근거는 신호 JSON + 검색 문서만 |
| 검증 | ① 규칙 가드레일(숫자·사업명 대조, 순수 함수) → ② Anthropic Claude 교차 검증(주장별 근거 판정, 구조화 JSON). 실패 시 1회 재생성 → 템플릿 |
| 스트리밍 | 리포트: 스트리밍 후 검증 결과 표시 / 챗봇: 검증 후 출력 |
| 오케스트레이션 | LangGraph — 리포트(재시도 고리) · 챗봇(Tool 판단). Q&A 는 일반 함수 |
| Tool | `search_policy`, `get_market_stats` |
| API | Pydantic 스키마, `web_mockup/AI_ROUTES.md` 계약, `X-Service-Token` |
| 평가 · 관측 | 골든셋(hit@3, 근거 충실도) + 요청 로그(doc_id · 토큰 · 지연) |

안 넣는 것: HNSW 인덱스 · 리랭커 · checkpointer · LLM 제공사 추상화 — 측정 근거가 생기면 넣는다.

---

## 스텝

- [x] **1. 스펙 확정** — 위 표
- [ ] **2. 문서 데이터 계약 + 실제 공고 정리** — 계약은 `app/schemas/policy_doc.py` 로 확정. 수동 6건 입력(2026-10-14, 일부 2차 출처 — 원문 대조 필요). 목표 15~20건 · 유형별 3건+ · 긴 공고 1~2건은 13스텝 수집으로 채운다
- [x] **3. 테이블 설계** — `supabase/migrations/20261011120000_policy_chunk.sql` (db push · 제약 확인 결과는 미확인)
- [x] **4. 적재** — `pipeline/doc/load_docs.py`. 6건 적재, 재실행 시 추가·변경·삭제 0
- [x] **5. 청킹** — 항목 단위 + 토큰 보조 분할 (6건 → 27조각, 최대 182토큰, 재실행 0건)
- [x] **6. 임베딩** — 배치 · NULL 인 조각만 · 배치마다 commit (27개, 재실행 0개)
- [x] **7. 검색** — 마감 제외 + 태그 우선 + RRF + 문서당 1개 (`python -m app.knowledge.retrieve` ok)
- [x] **8. 생성 + 규칙 가드레일** — `app/ai/report.py` · `app/domain/guardrail.py` · `report_context.py`. pytest 통과, 템플릿 5유형 통과 (실제 OpenAI 호출은 미확인)
- [x] **9. Claude 교차 검증** — `app/ai/verify.py` (tool 강제로 주장별 판정 JSON). supported 라도 인용이 근거 원문에 없으면 실패(`unsupported_claims`). 재생성 정책: 규칙 가드레일 → 교차 검증 순, 둘 중 하나라도 실패하면 위반 목록을 `feedback` 으로 넘겨 1회 재생성 → 또 실패면 템플릿. 실행은 10스텝 그래프 (실제 Claude 호출은 미확인)
- [ ] **10. Tool Calling + LangGraph** — 리포트 그래프 · 챗봇 그래프
- [ ] **11. API 연결** — FastAPI 엔드포인트 · 서비스 토큰 · 목업 연동
- [ ] **12. 평가 · 관측** — 골든셋 · 근거 충실도 집계 · 요청 로그
- [ ] **13. 정기 수집** — 아래 "수집 설계". 7~12스텝을 6건으로 끝까지 연결한 뒤 붙인다

---

## 수집 설계 (13스텝)

조사한 실제 구현(기업마당 API 문서, 공개 저장소 bosspickseoul #289 · jiwon-meo, K-Startup API)에서
공통으로 쓰는 방식을 따른다.

| 원천 | 주기 | 방식 | 사람 확인 |
|---|---|---|---|
| 기업마당 지원사업정보 API (`bizinfoApi.do`, 기업마당 발급 `crtfcKey`) | 매주 월 | `hashtags=서울` + 분야(금융 01 · 내수 05 · 경영 07). 1차 원천은 이것 하나 | PR 리뷰 |
| K-Startup 공고 API (data.go.kr 15125364) | 매주 월 | 재창업·재도전 공고만. 2차 | PR 리뷰 |
| 서울 상권분석서비스 (열린데이터광장 OA-22172 점포 · OA-22175 추정매출, 분기 갱신) | 매주 새 분기 확인 → 있을 때만 | prep 1~3단계 + `pipeline/load/` | `매핑 안 된 업종` 경고 0건일 때만 교체 |
| KOSIS · 신보 부실사유 | 연 1회 | 수동 | 사람 |
| 모델 재학습 | — | 자동 안 함 | 사람이 판단 (사전확률 보정값이 바뀐다) |
| 뉴스 · 블로그 | — | 안 가져옴 | — |

규칙
- **중복 키** `(source, external_id)` — 기업마당은 `pblancId`. 지금 `doc_id` 는 `bizinfo-PBLN_…` 꼴로 만든다.
- **필드 출처 구분** — 날짜(`reqstBeginEndDe`) · 기관 · URL · 신청방법은 API 값을 그대로 쓴다.
  한도 · 금리 · `sections` · `risk_type_tags` 는 LLM 이 본문/첨부에서 `PolicyDoc` 스키마로 구조화 출력 → Pydantic 검증.
  LLM 이 뽑은 숫자는 PR 리뷰에서 원문과 대조한다(가드레일은 근거가 틀린 것은 못 잡는다).
- **승인 = PR 머지** — 수집기는 `policy_docs.json` 을 고치는 PR 만 연다. 머지되면 load → chunk → build_index 가 돈다.
  검토 이력이 git 에 남고 별도 검토 화면이 필요 없다.
- **사라진 공고** — 원천에서 안 보이면 바로 지우지 않는다. `last_seen_at` 을 두고 30일 유예 뒤 삭제.
  마감은 검색 시 `apply_end` 로 이미 빠진다.
- **수집 실패 안전장치** — 수집 실패 또는 수집 건수가 직전의 50% 미만이면 삭제·숨김을 하지 않는다.
- **실행 위치** — GitHub Actions `schedule`. ai-service 는 외부에 열지 않으므로 Actions 가 Supabase 에 직접 붙는다.
  비밀값: `BIZINFO_KEY` · `OPENAI_API_KEY` · `DATABASE_URL`.
- ⚠ 첨부가 HWP 인 공고가 많다. `printFlpthNm`(본문출력 파일)으로 텍스트를 얻을 수 있는지 실제 호출로 먼저 확인한다.
- ⚠ 상권분석서비스는 2024년부터 공간 단위가 표준단위구역으로 바뀌었고 2026-07-03 부터 2021년 이후 자료만 준다.
  지금 zip 기반 prep 단계가 새 파일 형식과 맞는지 먼저 확인한다.

각 스텝의 상세(무엇을 · 어디에 · 왜 · 확인 방법)는 진행할 때 채운다.
