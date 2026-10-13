# RAG 파이프라인 작업 목록 (ai-service)

목표: 실무에 바로 적용할 수 있는 구조. 데모가 아니라 운영에서 터지는 지점을 처음부터 막는다.
코드는 직접 작성하고, 스텝은 하나씩 진행한다.

## 확정 스펙

| 영역 | 결정 |
|---|---|
| 문서 원천 | 실제 공고문을 직접 정리한 JSON (`ai-service/data/raw/policy_docs.json`). 자동 수집은 P2 — 같은 JSON 을 만드는 앞단으로 붙인다 |
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
- [ ] **2. 문서 데이터 계약 + 실제 공고 정리** — 계약은 `app/schemas/policy_doc.py` 로 확정. ⚠ `data/raw/policy_docs.json` 아직 없음 (15~20건, 유형별 3건+, 마감 공고 1~2건, 긴 공고 1~2건)
- [x] **3. 테이블 설계** — `supabase/migrations/20261011120000_policy_chunk.sql` (db push · 제약 확인 결과는 미확인)
- [x] **4. 적재** — `pipeline/doc/load_docs.py` 작성 완료. JSON 이 없어 실제 실행 · 멱등성 확인은 아직
- [ ] **5. 청킹** — 항목 단위 + 토큰 보조 분할
- [ ] **6. 임베딩** — 배치 · NULL 인 조각만 · 배치마다 commit
- [ ] **7. 검색** — 마감 제외 + 태그 우선 + RRF + 문서당 1개
- [ ] **8. 생성 + 규칙 가드레일** — 프롬프트 · 스트리밍 · `app/domain/guardrail.py` + pytest
- [ ] **9. Claude 교차 검증** — 주장 분해 · 근거 판정 · 재생성 정책
- [ ] **10. Tool Calling + LangGraph** — 리포트 그래프 · 챗봇 그래프
- [ ] **11. API 연결** — FastAPI 엔드포인트 · 서비스 토큰 · 목업 연동
- [ ] **12. 평가 · 관측** — 골든셋 · 근거 충실도 집계 · 요청 로그

각 스텝의 상세(무엇을 · 어디에 · 왜 · 확인 방법)는 진행할 때 채운다.
