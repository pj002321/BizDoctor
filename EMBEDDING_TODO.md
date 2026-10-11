# RAG 파이프라인 작업 목록 (ai-service)

참고 구현: `G:\Safe-Farm\ai-service` — 같은 폴더 구조(`app/knowledge` · `app/graph` · `app/tools` · `pipeline/doc`)라
파일 단위로 대응시켜 옮긴다. 다만 문서 수가 다르다(Safe-Farm 수천 조각 / 우리 8건 → P2 자동 수집 후 수백 건).
규모 때문에 생긴 장치(HNSW 반복 훑기, halfvec, 소스 다양화)는 가져오지 않는다.

브랜치: `development` 에서 `feature/rag-pipeline` 을 따서 작업한다.

## 전체 흐름

```
[색인 — pipeline/doc, 배치]
rag_documents.py ─ 1.적재 ─▶ policy_doc ─ 3.청킹 ─▶ policy_chunk ─ 4.임베드 ─▶ policy_chunk.embedding
                  (해시 비교)              (토큰 단위)               (NULL 인 것만)

[질의 — app/, 요청마다]
질문 ─┬─ plan(Tool Calling 할지?) ── run_tools(진단·상권 조회) ─┐
      └─ retrieve(태그 우선 + 벡터·키워드 RRF) ──────────────────┴─ generate ─ guardrail ─▶ 답변
                                    ↑ 7.LangGraph 가 이 그래프를 조립한다
```

| 단계 | 우리 파일 | Safe-Farm 대응 |
|---|---|---|
| 의존성 | `ai-service/pyproject.toml` | 같은 파일 |
| 스키마 | `supabase/migrations/…_policy_chunk.sql` | `app/models/document.py`, `chunk.py` |
| 적재 | `pipeline/doc/load_docs.py` | `pipeline/doc/load_data.py` |
| 청킹 | `app/knowledge/chunker.py`, `pipeline/doc/chunk.py` | 같은 이름 |
| 벡터라이징 | `app/knowledge/embed.py` | `app/knowledge/embedder.py` |
| 임베드 | `pipeline/doc/embed.py` | 같은 이름 |
| 검색 | `app/knowledge/retrieve.py` | `retriever.py`, `vector_store.py` |
| 생성 | `app/knowledge/generator.py` | 같은 이름 |
| 가드레일 | `app/domain/guardrail.py` | 같은 이름 |
| Tool Calling | `app/tools/tools.py` | 같은 이름 |
| LangGraph | `app/graph/state.py`, `nodes.py`, `graph.py` | 같은 이름 |
| 평가 | `eval/golden.py` | `pipeline/doc/golden.py` |

---

## 0단계. 의존성 추가

- [ ] `pyproject.toml` 에 `tiktoken`, `langchain-text-splitters`, `langgraph`, `langchain-core`, `fastapi`, `uvicorn` 추가
- [ ] `.\.venv\Scripts\python.exe -m pip install -e ai-service`
- [ ] 확인: `python -c "import tiktoken, langgraph, langchain_text_splitters"`

**왜?** 청킹은 토큰 수를 세야 하고(tiktoken), 한국어 문장 경계로 자르는 분할기(text-splitters)와
그래프 엔진(langgraph)이 필요하다. 지금 venv 에는 `tiktoken` 조차 없다.
의존성 목록은 `pyproject.toml` 한 곳에만 둔다 — 두 군데 두면 한쪽만 고쳐진다.

커밋: `chore: RAG 의존성 추가 — 청킹·그래프에 tiktoken·text-splitters·langgraph 가 필요하다`

---

## 1단계. 문서 원본 정리 + 스키마 나누기

### 1-1. 문서 원본 (`pipeline/doc/rag_documents.py`)
- [ ] 각 문서에 `agency`, `target`, `limit_amount`, `rate`, `apply_period`, `url` 추가 (⚠ 공고 원문 그대로, 모르면 `None`)
- [ ] 금액·금리·기간 같은 **숫자는 본문(content)에서 빼서** 위 필드로 옮긴다

**왜 숫자를 본문에서 빼나?** 본문에 숫자가 섞이면 "한도 5억원, 금리 2%" 같은 문장 때문에 문서들이 서로 비슷한
벡터가 되어 검색이 흐려진다. 검색은 "무슨 제도인가"(본문)로 하고, 답변에 쓸 숫자는 필드에서 꺼낸다.
(Safe-Farm `document.py` 의 `meta` 와 같은 원칙.) 또 가드레일이 "답변의 숫자가 원본에 있나"를 대조하려면
숫자가 정해진 칸에 있어야 한다.

### 1-2. 스키마 (`supabase/migrations/YYYYMMDDHHMMSS_policy_chunk.sql`)
- [ ] `policy_doc` 에 `content_hash text not null` 추가, `embedding` · `fts` 컬럼 제거
- [ ] `policy_chunk` 신설: `id`, `doc_id → policy_doc on delete cascade`, `chunk_index`, `body`, `n_tokens`,
      `embedding vector(1536)`(NULL = 아직 안 함), `fts` generated, `unique(doc_id, chunk_index)`
- [ ] 확인: Supabase 에 적용 후 `\d policy_chunk`

**왜 테이블을 나누나?** 지금은 문서 1건 = 벡터 1개다. 공고문이 길어지면 한 문서를 여러 조각으로 잘라야 하는데,
그러면 "문서 정보(제목·기관·태그)"와 "조각(본문·벡터)"이 1:N 이 된다. 태그·한도 같은 문서 정보는
`policy_doc` 에 한 번만 두고, 검색 대상인 조각은 `policy_chunk` 에 둔다.
`on delete cascade` 는 문서를 지우면 조각도 같이 지워지게 한다 — 남으면 없는 문서가 검색된다.

커밋: `update: 정책 문서를 문서·조각 테이블로 분리 — 긴 공고문을 청킹하려면 1:N 이 필요하다`

---

## 2단계. 적재 (`pipeline/doc/load_docs.py`, 기존 `build_index.py` 대체)

- [ ] `rag_documents.py` → `policy_doc` upsert. 본문 sha256 을 `content_hash` 에 저장
- [ ] 해시가 바뀐 문서는 조각을 지운다(다음 단계가 다시 자른다). 그대로면 건드리지 않는다
- [ ] 원본에서 사라진 `doc_id` 는 DB 에서 삭제
- [ ] 저장 **전에** assert: `doc_id` 중복 없음, `RISK_TYPE_QUERY`(app/domain/signal.py) 의 5개 유형마다 태그 문서 ≥ 1
- [ ] 확인: 두 번 연속 실행 → 두 번째는 "변경 0건". 문서 하나 빼고 실행 → DB 에서도 사라짐

**왜?**
- **해시 비교:** 본문이 안 바뀐 문서를 다시 자르고 임베딩하면 돈만 든다. "바뀐 것만"의 기준이 해시 하나다.
- **삭제:** 마감된 지원사업을 원본에서 지워도 DB 에 남으면 계속 추천된다.
- **커버리지 assert:** 어떤 위험 유형에 맞는 문서가 없으면 그 유형 사용자에게 추천이 빈 목록으로 나간다.
  오류 없이 조용히 빠지므로 적재할 때 막는다.

커밋: `feature: 정책 문서 적재 단계 — 해시로 바뀐 문서만 재색인하고 지운 문서를 정리한다`

---

## 3단계. 청킹 (`app/knowledge/chunker.py` + `pipeline/doc/chunk.py`)

- [ ] `chunker.py`: `CHUNK_SIZE = 480`(토큰), `CHUNK_OVERLAP = 48`,
      구분자 `["\n\n", "\n", "다. ", "요. ", ". ", ", ", " ", ""]`. 잘렸을 때만 조각 앞에 `[제목] ` 을 붙인다
- [ ] `chunk.py`: 조각이 하나도 없는 문서만 잘라 `policy_chunk` 에 넣는다(`--rebuild` 면 전부)
- [ ] 확인: 지금 8건은 전부 1조각이어야 한다(300자 ≪ 480토큰). 긴 텍스트로 `split_text` 를 불러 여러 조각이 나오는지 본다

**왜?**
- **왜 자르나:** 한 조각에 주제가 여러 개 섞이면 벡터가 평균으로 뭉개져 어느 질문에도 애매하게 걸린다.
  모델 한도(8191)가 아니라 그보다 훨씬 작은 480 으로 자르는 이유다.
- **왜 겹치게(overlap):** 경계에서 잘린 문장의 앞뒤 문맥을 다음 조각이 이어받는다.
- **왜 "다. " 같은 구분자:** 한국어는 공백만으로 문장 끝을 알 수 없다. 종결어미에서 자르면 문장이 덜 끊긴다.
- **왜 제목을 붙이나:** "신청 대상은 …" 같은 조각만 보면 무슨 제도인지 모른다. 제목이 있어야 검색에 걸린다.
- **자르는 법(app)과 저장(pipeline)을 나누는 이유:** 자르는 규칙은 DB 없이 테스트할 수 있어야 한다.

커밋: `feature: 정책 문서 청킹 — 긴 공고문이 한 벡터로 뭉개지지 않게 토큰 단위로 자른다`

---

## 4단계. 벡터라이징 + 임베드

### 4-1. 벡터라이징 (`app/knowledge/embed.py`)
- [ ] `EMBED_BATCH_SIZE` 단위로 나눠 호출, 응답을 `index` 로 정렬, 차원이 `DIMENSION` 이 아니면 `ValueError`
- [ ] OpenAI 클라이언트는 처음 쓸 때 만든다(키 없으면 import 만으로 죽지 않게)

**왜?** 텍스트 → 숫자 벡터로 바꾸는 함수다. 색인과 질문 검색이 **반드시 이 함수 하나**를 써야 한다 —
둘이 다른 모델을 쓰면 벡터끼리 비교가 안 된다. 배치로 나누는 건 API 의 요청당 한도 때문이고,
차원 검사는 잘못된 벡터가 DB INSERT 에서야 터져 원인을 못 찾는 걸 막는다.

### 4-2. 임베드 (`pipeline/doc/embed.py`)
- [ ] `embedding IS NULL` 인 조각을 배치로 가져와 벡터를 채우고 **배치마다 commit**
- [ ] `--full` 이면 전부 NULL 로 지우고 다시(모델을 바꿨을 때만)
- [ ] 확인: `SELECT count(*) FROM policy_chunk WHERE embedding IS NULL` → 0. 다시 돌리면 "할 게 없다"

**왜?** 돈이 드는 단계라서 "NULL 인 것만" 이 기본이다. 중간에 끊겨도 commit 된 데까지는 남아서
다시 돌리면 남은 것부터 이어 한다. 같은 조각에 두 번 돈을 쓰지 않는다.

커밋: `feature: 조각 증분 임베딩 — NULL 인 조각만 배치로 채워 끊겨도 이어서 한다`

---

## 5단계. 검색 (`app/knowledge/retrieve.py`)

- [ ] 검색 대상을 `policy_doc` → `policy_chunk JOIN policy_doc` 으로 바꾼다
- [ ] 정렬 규칙은 그대로: ① `risk_type` 태그 일치 문서 먼저 ② 그 안에서 벡터·키워드 순위 RRF
- [ ] 같은 문서의 조각이 여러 개 걸리면 문서당 최고 점수 하나만 남긴다
- [ ] `retrieve(query, risk_type, top_k)` 시그니처 유지 → `rag_pipeline.py`, `signal.py` 는 안 고친다
- [ ] 확인: `python -m app.knowledge.retrieve` → `ok`

**왜?**
- **태그 우선:** 모델이 "고금리_과다채무형" 이라고 판단했으면 채무조정 제도가 먼저 나와야 한다. 벡터 유사도만
  믿으면 문장이 비슷한 다른 유형 제도가 1등이 될 수 있다.
- **RRF:** 벡터 점수(0~2)와 키워드 점수는 범위가 달라 그냥 더할 수 없다. 그래서 "몇 등인가"만 써서 합친다.
- **문서당 하나:** 추천 카드는 문서 단위다. 같은 제도가 조각 수만큼 세 칸을 차지하면 안 된다.

커밋: `update: 검색을 조각 단위로 — 청킹 후에도 문서당 한 번만 추천한다`

---

## 6단계. 생성 + 가드레일

### 6-1. 생성 (`app/knowledge/generator.py`)
- [ ] `build_context(docs)`: 조각마다 `[제목 · 기관]` 머리 + 본문 + `한도/금리/신청기간` 한 줄
- [ ] 시스템 프롬프트: "신호 JSON 과 참고 자료**만** 근거로, 그 밖의 지식 금지"(FLOW.md 5장),
      "83.8% 를 예측력이라 말하지 말 것", "신호등/진단 등급 용어 구분"
- [ ] 스트리밍(`stream=True`)으로 토큰을 흘린다

**왜?**
- **제목 머리:** 이게 없으면 LLM 이 A 제도의 금리를 B 제도 이름에 붙인다(Safe-Farm 에서 실제로 났다).
- **"자료만":** 금액·금리·신청기간은 지어내면 바로 사용자 피해다. 모르면 모른다고 하게 한다.
- **스트리밍:** 첫 글자가 3초 안에 보여야 한다(FLOW.md 5장).

### 6-2. 가드레일 (`app/domain/guardrail.py` + `ai-service/tests/test_guardrail.py`)
- [ ] 순수 함수: 답변에서 숫자·금액·지원사업명을 뽑아, 컨텍스트에 없는 것을 돌려준다
- [ ] 걸리면 1회 재생성, 또 걸리면 템플릿 문장으로 대체
- [ ] 확인: pytest — "한도 5억원"(있음) 통과 / "한도 7억원"(없음) 걸림

**왜?** 프롬프트로 "지어내지 마" 해도 LLM 은 가끔 지어낸다. 생성 **후에** 기계적으로 대조하는 게 마지막 방어선이다(F-LLM-02).
DB·LLM 없이 테스트돼야 해서 `app/domain/` 에 둔다(AGENTS.md 규칙).

커밋: `feature: 리포트 생성·수치 가드레일 — 컨텍스트에 없는 금액·사업명을 막는다`

---

## 7단계. Tool Calling + LangGraph

### 7-1. 도구 선언 (`app/tools/tools.py`)
- [ ] `TOOL_SPECS` (OpenAI function-calling 형식, 실행 로직 없음)
  - `get_diagnosis(diagnosis_id)` — 이 사용자의 진단 등급·추정 원인·신호 JSON
  - `get_market_stats(gu, industry)` — 자치구 × 업종 폐업률·신호등(`region_risk`)

**왜?** "제 가게 상황에서 뭘 신청해야 하죠?" 는 문서 검색만으로 답할 수 없다 — 이 사람의 진단 결과가 있어야 한다.
LLM 에게 "필요하면 이 함수를 불러 달라"고 목록을 주면, 어떤 질문에 DB 조회가 필요한지 LLM 이 고른다.
선언만 두고 실행은 노드가 한다 — LLM 이 우리 코드를 직접 실행하지 않게.

⚠ 의존: `region_risk` 적재(`pipeline/load/`, F-SYS-03)와 진단 결과 테이블(F-DIA-08)이 아직 없다.
그 전까지는 `get_market_stats` 를 CSV(`risk_weights_by_region_industry.csv`)에서 읽거나 이 단계를 뒤로 미룬다.

### 7-2. 그래프 (`app/graph/state.py`, `nodes.py`, `graph.py`)
- [ ] `state.py`: `question`, `history`, `diagnosis_id`, `risk_type`, `tool_calls`, `tool_result`, `docs`, `answer`, `retry`
- [ ] `nodes.py`: `plan`(도구 필요?) · `run_tools` · `retrieve` · `generate` · `check`(가드레일) — 각 노드는 바꾼 키만 dict 로 돌려준다
- [ ] `graph.py`:
  ```
  START ┬─ plan ──(도구?)── run_tools ─┐
        └─ retrieve ───────────────────┴─ generate(defer=True) ─ check ─(실패·1회)─▶ generate
                                                                      └─(통과/재실패)─▶ END
  ```
- [ ] 확인: 도구가 필요 없는 질문 / 필요한 질문 각각 `graph.invoke` → generate 가 **한 번만** 도는지

**왜?**
- **왜 그래프로:** "도구 부를지 판단 → 조회 → 검색 → 생성 → 검사 → 실패 시 재생성" 은 분기와 되돌아감이 있는 흐름이다.
  if 문으로 짜면 금방 꼬인다. 노드를 따로 떼면 하나씩 테스트할 수 있다.
- **plan ∥ retrieve 병렬:** 검색은 plan 결과가 필요 없다. 나란히 돌리면 LLM 판단을 기다리는 동안 검색이 끝난다.
- **`defer=True`:** 합류 노드는 기본적으로 먼저 온 쪽만으로 한 번 돈다. 빼면 generate 가 두 번 돌고,
  첫 번째는 진단 정보 없이 답한다(Safe-Farm 에서 실제로 났다).
- ⚠ **plan 에서 DB 를 만지지 않는다.** retrieve 와 다른 스레드로 동시에 돌아서 DB 세션이 엉킨다.

커밋: `feature: 상담 그래프 — 진단 조회 Tool Calling 과 정책 검색을 합쳐 답한다`

---

## 8단계. API 연결 (`app/api/`, `app/main.py`)

- [ ] `web_mockup/AI_ROUTES.md` 계약대로: `POST /api/report`(스트리밍) · `POST /api/chat` · `POST /api/chatbot`
- [ ] 모든 요청에 `X-Service-Token` 검사(AGENTS.md — 이 서버는 공개 인터넷에 열지 않는다)
- [ ] 확인: `uvicorn app.main:app` 후 `BACKEND_URL=http://localhost:8000` 로 목업에서 호출

**왜?** 프론트 목업이 이미 이 경로·모양으로 부르고 있다. 같은 계약으로 만들면 프론트는 환경변수 하나만 바꾸면 된다.

커밋: `feature: RAG API 엔드포인트 — 목업 계약 그대로 리포트·Q&A·챗봇을 연다`

---

## 9단계. 골든셋 평가 (`ai-service/eval/golden.py` + `data/golden/rag.csv`)

- [ ] CSV: `질문, risk_type, 기대_doc_id`(여러 개면 `|`). 유형별 3문항 이상
- [ ] 검색만 돌려 hit@3(기대 문서가 3등 안에 있나)을 센다. **답변 문장은 보지 않는다**
- [ ] 확인: 문서·청킹 규칙·검색식을 바꿀 때마다 돌려서 점수가 떨어지지 않는지

**왜?**
- **왜 필요:** 청킹 크기나 검색식을 바꿨을 때 "좋아졌나?" 를 감으로 판단할 수 없다. 숫자로 비교한다.
- **왜 답변을 안 보나:** LLM 답변은 매번 달라서 실패가 신호가 안 된다. 흔들리지 않는 건 "어느 문서가 뽑혔나" 다.
- **왜 pytest 가 아닌가:** 문항마다 임베딩 API 비용이 든다. 사람이 필요할 때 돌린다.

커밋: `feature: RAG 검색 골든셋 — 청킹·검색식을 바꿀 때 회귀를 숫자로 잡는다`

---

## 지금은 안 하는 것

| 항목 | 이유 | 할 때 |
|---|---|---|
| HNSW 인덱스 · halfvec | 수백 건 이하면 전수 비교가 더 빠르고 용량도 작다 | 조각 수천 건 |
| 이웃 조각(neighbors) 확장 | 지금은 문서당 1조각이라 이웃이 없다 | 긴 공고문 청킹 후 골든셋 hint 가 낮을 때 |
| 리랭커 | RRF 가 이미 어휘 일치를 반영한다 | 골든셋에서 순위가 흔들릴 때 |
| 한국어 형태소 키워드 검색 | `'simple'` 설정이 조사를 못 떼지만 벡터가 보완한다 | 골든셋에서 키워드형 질문이 틀릴 때 |
| checkpointer(멀티턴 저장) | 대화 이력은 요청에 `history` 로 실려 온다(최대 10개) | 서버가 대화를 기억해야 할 때 |
