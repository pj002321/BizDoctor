# AGENTS.md

이 저장소에서 작업할 때 지켜야 할 규칙과 구조.

## 프로젝트

**상권 신호등** — 서울시 상권 통계로 소상공인의 경영 위기를 예측하고, 위기를 6개
`risk_type` 중 하나로 분류한 뒤, 맞는 2026년 정부 지원사업을 RAG 로 찾아 준다.

요구사항은 `docs/` 에 있다. 코드보다 먼저 본다.

| 문서 | 내용 |
|---|---|
| `docs/기능정의서.csv` | 기능 목록 (F-MAP · F-DIA · F-RAG · F-LLM · F-SYS) |
| `docs/스펙.md` | 각 기능을 무엇으로 구현하는지, 반드시 지켜야 할 것 |
| `docs/schema.png` | ERD |

## 구조

```
BizDoctor/
├── src/                  Next.js 웹 — app/(라우팅) · features/(기능) · components/ · shared/
├── ai-service/           Python AI 서버
│   ├── app/                FastAPI — api · core · domain · model · knowledge · repo · schemas · service
│   ├── pipeline/           배치 스크립트 — prep · train · load · doc · analysis
│   ├── data/raw/           원본 데이터 (서울 zip 3개 · KOSIS xlsx · sgf176 csv)
│   └── tests/
├── supabase/migrations/  DB 스키마
└── docs/                 도메인 자료
```

## 아키텍처 규칙

### 웹 (`src/`)

- `src/app/` 은 **라우팅 전용**이다. 로직은 `src/features/<기능>/` 에 둔다.
- 의존 방향은 `shared → features → app` 한쪽뿐이다. **features 끼리 import 하지 않는다.**
- 순수 함수는 `features/<기능>/domain/` 에 둔다. 테스트는 여기에만 쓴다.

### AI 서버 (`ai-service/`)

- `app/domain/` 에는 순수 함수만 둔다 — 사전확률 보정, 매출 지수 정규화, 가드레일
  수치 대조처럼 틀리면 사고가 나는 로직이다. DB·모델 없이 테스트할 수 있어야 한다.
- `app/core/config.py` 가 환경값과 경로를 한 곳에서 정한다. 다른 파일이 경로를
  제멋대로 정하지 않는다.
- 이 서버는 **공개 인터넷에 열지 않는다.** LLM 을 호출하므로 Next.js 서버만 내부망
  + `X-Service-Token` 으로 호출한다.

### 역할 분담

- **읽기 전용 상권 조회(F-MAP)**: Next.js Server Component 가 Postgres 를 직접 읽는다.
- **추론 · RAG · LLM(F-DIA · F-RAG · F-LLM)**: ai-service 를 거친다. 모델(Keras)과
  인덱스가 Python 쪽에 있기 때문이다.

## 반드시 지킬 것

`docs/스펙.md` 6장의 요약이다. 어기면 틀린 결과가 사용자에게 그대로 나간다.

1. **두 결과를 섞지 않는다(F-SYS-01).** "신호등"은 지역(행정동 × 업종) 결과에만 쓰고,
   사업장 결과는 "진단 등급"이라 부른다. URL(`/market` vs `/diagnosis`)·색 범례·
   features 폴더도 분리한다.
2. **사전확률 보정 없이 배포하지 않는다(F-DIA-04).** 학습 위험군 비중은 0.30,
   실제 서울은 약 0.14 다. 빼먹으면 전 사용자의 위험도가 부풀려진다.
3. **정확도를 "예측력"이라 쓰지 않는다(F-SYS-08).** 83.8% 는 시뮬레이션 규칙을
   되찾은 비율일 뿐이다(아래 "학습 데이터의 순환" 참고).
4. **점포 수 5 이하 셀에는 "표본 적음" 배지를 단다.** 폐업률이 0/33/67% 같은
   계단값이 되고, 최댓값 300% 도 점포 1개 셀에서 나온다.
5. **매출 실금액을 저장하지 않는다(F-SYS-05).** 1개월차 = 100 인 지수만 저장한다.

## 도메인

### 실제 데이터 3종과 각각이 정하는 것

가게별 월매출은 공개 데이터가 아니다. 그래서 매출은 시뮬레이션하되, 양 끝을 실제
통계로 맞춘다.

1. **서울시 상권분석서비스 점포-행정동** (zip 3개, 2023~2025, 12개 분기) — 실제 패널.
   관측 단위는 분기별 `행정동 × 서비스_업종`. 지역·업종 위험 기준선과 회귀 타깃
   `다음분기_폐업률` (`groupby(...).shift(-1)`) 을 준다.
2. **KOSIS 사업체운영 애로사항 xlsx** — YELLOW 기업이 *왜* 힘든지 정한다.
   `원가상승_확률 = (원재료비 + 최저임금영향) / (그 합 + 동일업종경쟁심화 + 보증금월세)`,
   업종별로 `yellow_subtype_prob.csv` 에 쓴다.
3. **신용보증기금 채권관리 (`sgf176_*.csv`)** — RED 기업이 *왜* 무너지는지 정한다.
   실제 부실사유코드 분포를 `CAUSE_TO_RISKTYPE` 으로 매핑해 표본을 뽑는다.

### `KOSIS_산업1` — 두 데이터를 잇는 유일한 키

`preprocess_seoul_panel.py` 의 `INDUSTRY_MAP` 이 약 100개 `서비스_업종_코드_명` 을
약 12개 KOSIS 산업중분류로 묶는다. 이 컬럼이 서울 패널과 KOSIS 를 잇는 **유일한**
다리이자 모델의 one-hot 피처다.

- 새 업종명이 나오면 `⚠ 매핑 안 된 업종` 경고가 뜨고 그 행은 `NaN` 이 된다.
  경고를 무시하지 말고 `INDUSTRY_MAP` 을 넓힌다.
- 알려진 근사 두 가지: 보건업(의원·치과·한의원·동물병원)은 `협회 및 단체...` 에
  넣었고, 매핑 안 된 업종은 `yellow_subtype_prob.csv` 에서 `전산업` 으로 폴백한다.

### 6개 `risk_type` — 시스템의 뼈대

```
정상_유지형       → GREEN
단기_매출_정체형  → YELLOW     원가_상승_부담형  → YELLOW
매출_폭락형       → RED        고금리_과다채무형 → RED      상권_침체_붕괴형 → RED
```

모델은 `risk_type` 을 예측한다. `risk_level` 과 UI 테마는 여기서 표를 찾아 정할 뿐이다.

⚠ 이 분류가 **네 파일에 중복**돼 있다. 유형을 바꾸거나 추가하면 넷 다 고친다.
`app/domain/` 한 곳으로 모으기 전까지 유효한 경고다.

- `pipeline/train/generate_synthetic_timeseries.py` — `CAUSE_TO_RISKTYPE` (라벨 부여)
- `pipeline/train/train_risk_model.py` — `RISKTYPE_TO_LEVEL`
- `pipeline/doc/rag_pipeline.py` — `RISK_TYPE_QUERY`, `RISK_TYPE_TO_LEVEL`
  (키가 하나라도 빠지면 `build_signal_json` 이 `KeyError`)
- `pipeline/doc/rag_documents.py` — 모든 문서의 `risk_type_tags`

### 학습 데이터의 순환 — 성능 수치를 읽는 법

`generate_synthetic_timeseries.py` 는 `폐업률_업종내_percentile` 로 `risk_level` 을
정하고(0.75 분위 초과면 RED), 그 등급으로 6개월 매출을 만든다(`TREND_BY_LEVEL`).
`train_risk_model.py` 는 첫 3개월 매출과 **같은 percentile** 을 입력으로 받는다.
그러니 정확도는 실제 예측력이 아니라 생성기 규칙을 되찾은 정도다.

RED 3유형은 생성기가 같은 궤적에서 뽑으므로 원리적으로 구분할 수 없다
(원가상승·상권침체 재현율 0%). 서비스에는 "추정 원인" + 확률로만 노출한다.

모델 구조: `(N, 3, 1)` 매출 시퀀스(1개월차 기준 상대값)에 `LSTM(16)`, 정적 피처
(percentile, 프랜차이즈 비중, 업종 one-hot)에 Dense 가지를 두고 둘을 합친다.
RED 재현율이 우선이라 `class_weight="balanced"`.

### RAG

지금은 `rag_documents.py` 의 하드코딩 문서 8건에 TF-IDF + 코사인이다. 임베딩으로
바꾸되 인터페이스 `SimpleRAGIndex.retrieve(query, risk_type, top_k)` 는 유지한다.
검색은 `risk_type` 태그로 먼저 거르고 유사도로 순위를 매긴다. `build_signal_json`
이 프론트 계약(`risk_level`, `score`, `visual_theme`, `solutions[]`)을 만든다.
`_similarity_score` 는 디버그 전용이다 — 운영 응답에서 뺀다.

## 파이프라인

Python 3.11 venv (TensorFlow CPU 2.21 / Keras 3, pandas 3, scikit-learn, openpyxl,
pyarrow). 의존성이 없으면 전역이 아니라 `.venv` 에 설치한다.

단계는 순서가 고정이다. 각 단계가 앞 단계의 출력 파일을 읽는다.

| 순서 | 스크립트 | 출력 |
|---|---|---|
| 1 | `prep/0_merge_seoul_zips.py` | `seoul_panel_raw.parquet` |
| 2 | `prep/preprocess_seoul_panel.py` | `seoul_panel_model_ready.csv` (~53MB) |
| 3 | `prep/join_kosis_hardship.py` | `kosis_hardship_full.csv`, `yellow_subtype_prob.csv` |
| 4 | `train/generate_synthetic_timeseries.py` | `synthetic_companies.csv`, `synthetic_sales_timeseries.csv` |
| 5 | `train/train_risk_model.py` | `risk_model.keras`, `model_predictions_sample.csv` |
| — | `doc/rag_pipeline.py` | 데모: 5개 risk_type 의 신호 JSON 출력 |

느린 건 5단계뿐이다(60 epoch, `val_loss` 조기 종료). 재실행하면 출력을 그 자리에서
덮어쓴다 — 버전 관리 없음.

`analysis/` (mongo · warehouse · sql · tableau) 는 분석·발표용이다. 서비스 런타임과 무관하다.

### ⚠ 알려진 문제: 구조 이동 후 경로가 깨져 있다

스크립트가 아직 **cwd 기준 상대경로**를 하드코딩한다(`rawdata/...`, `seoul_panel_raw.parquet` 등).
원본은 `ai-service/data/raw/` 로 옮겨졌으므로 지금 그대로 돌리면 파일을 못 찾는다.
`app/core/config.py` 의 `DATA_DIR` (`__file__` 기준 절대경로) 로 옮기기 전까지 실행하지 않는다.

## 인코딩 (Windows · 한글 — 버그가 반복해서 나는 곳)

- zip 안의 서울시 CSV 는 **cp949**. 생성하는 CSV 는 전부 **utf-8-sig**. DB 에 적재할
  때도 인코딩을 명시한다.
- `sgf176_utf8.csv` 는 헤더가 깨져 있다(`부?�사?�코??`). 그래서 스크립트는
  `sgf176_utf8_bom.csv` 를 **먼저** 읽고, 실패하면 깨진 원본으로 폴백하며, 부실사유코드
  컬럼은 **위치로** 고른다(`sgf.columns[6]`). 원본을 다시 인코딩하기 전에는 이름 기반
  조회로 "고치지" 않는다.
- KOSIS xlsx 의 `시도별(1)` 은 **병합 셀**이라 openpyxl 은 지역별 첫 행 외엔 빈칸을 준다.
  `join_kosis_hardship.py` 가 `last_region` 을 앞으로 채워 메운다. 지우면 서울특별시가
  `전산업` 한 행으로 조용히 줄어든다(실제로 났던 버그).
- DataFrame · CSV 컬럼명은 전부 한글이다. 새 컬럼도 한글로 짓는다.

## 형상 관리

### 브랜치

```
feature/* → development → production
```

- 모든 작업은 `development` 에서 딴 `feature/작업명` 에서 한다.
- `development` · `production` 에 직접 커밋하지 않는다.

### 커밋 메시지

```
<태그>: <무엇을 왜 바꿨는지>
```

| 태그 | 쓰는 때 |
|---|---|
| `feature` | 새 기능 추가 |
| `update` | 기존 기능 변경 |
| `fixed` | 오류 수정 · 리팩토링 |
| `chore` | 라이브러리 · 버전 · 도구 |
| `wip` | 작업 중 일시 중단 (`feature/*` 안에서만) |
| `broken` | 빌드 불가 — 받지 말 것 (`feature/*` 안에서만) |

- 한 커밋은 한 가지 이유로만 바꾼다.
- 본문에는 **왜** 를 쓴다. 무엇은 diff 가 말해 준다.
