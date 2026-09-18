# AGENTS.md

Guidance for working with the code in this repository.

## Project

"상권 신호등" (Commercial District Traffic Light) — predicts small-business (소상공인) financial distress from Seoul commercial-district statistics, classifies the distress into one of six `risk_type` categories, and retrieves matching 2026 government support programs via RAG.

Not a package or app — a linear batch pipeline of standalone scripts. No test suite and no CLI argument parsing: every script hardcodes its input/output filenames relative to the current directory, so **all scripts must be run from the project root**.

Repo layout: pipeline scripts live in `src/`, the four real source datasets in `rawdata/` (3 Seoul zips, the KOSIS xlsx, `sgf176_utf8*.csv`), and every derived artifact is written to the project root — the large ones (`seoul_panel_model_ready.csv`, `shinhan_warehouse.db`, `tableau/tableau_panel.csv`, …) are gitignored because they are regenerable.

## Commands

Uses a local venv (Python 3.11, TensorFlow CPU 2.21 / Keras 3, pandas 3, scikit-learn, openpyxl, pyarrow). There is no requirements file; if a dependency is missing, install it into `.venv` rather than globally.

```powershell
.\.venv\Scripts\python.exe src\<script>.py     # run any pipeline stage
.\.venv\Scripts\pip.exe list               # inspect installed deps
```

The pipeline stages are strictly ordered — each consumes the previous stage's output file:

```powershell
.\.venv\Scripts\python.exe src\0_merge_seoul_zips.py           # 3 zips        -> seoul_panel_raw.parquet
.\.venv\Scripts\python.exe src\preprocess_seoul_panel.py       # parquet       -> seoul_panel_model_ready.csv (~53MB)
.\.venv\Scripts\python.exe src\join_kosis_hardship.py          # KOSIS xlsx    -> kosis_hardship_full.csv, yellow_subtype_prob.csv
.\.venv\Scripts\python.exe src\generate_synthetic_timeseries.py# above + sgf   -> synthetic_companies.csv, synthetic_sales_timeseries.csv
.\.venv\Scripts\python.exe src\train_risk_model.py             # synthetic     -> risk_model.keras, model_predictions_sample.csv
.\.venv\Scripts\python.exe src\rag_pipeline.py                 # demo: prints signal JSON for 5 sample risk_types
.\.venv\Scripts\python.exe src\rag_documents.py                # lists the RAG corpus
```

`train_risk_model.py` is the only slow stage (60 epochs, early stopping on `val_loss`). Everything else runs in seconds to a couple of minutes. Re-running a stage always overwrites its outputs in place — there is no versioning of artifacts.

## Architecture

### The three real datasets, and what each one anchors

The core design claim (documented in the script docstrings) is that per-store monthly revenue is not public data, so the simulation is **calibrated at both ends by real statistics** rather than invented:

1. **서울시 상권분석서비스 점포-행정동** (3 zips, 2023–2025, 12 quarters) → the real panel. Unit of observation is `행정동 × 서비스_업종` per quarter. Supplies the geographic/industry risk baseline and the regression target `다음분기_폐업률` (next-quarter closure rate, produced by a `groupby(...).shift(-1)`).
2. **KOSIS 사업체운영 애로사항 xlsx** → decides *why* a YELLOW company is struggling. `원가상승_확률 = (원재료비+최저임금영향) / (그것 + 동일업종경쟁심화+보증금월세)`, per industry, written to `yellow_subtype_prob.csv`.
3. **신용보증기금 채권관리 (`sgf176_utf8.csv`)** → decides *why* a RED company fails. The real 부실사유코드 distribution is mapped through `CAUSE_TO_RISKTYPE` and sampled from.

### The `KOSIS_산업1` join key

`INDUSTRY_MAP` in `preprocess_seoul_panel.py` collapses the ~100 `서비스_업종_코드_명` values into the ~12 KOSIS 산업중분류 labels. This column is the *only* bridge between the Seoul panel and the KOSIS hardship data, and it is also a one-hot model feature. If a new 업종 name appears, the script prints a `⚠ 매핑 안 된 업종` warning and those rows get `NaN` — extend `INDUSTRY_MAP`, don't ignore it. Two known approximations already live there: 보건업 (의원/치과/한의원/동물병원) is parked under 협회 및 단체..., and `전산업` is the fallback key looked up in `yellow_subtype_prob.csv` for unmapped industries.

### The six `risk_type` labels are the system's spine

```
정상_유지형        -> GREEN
단기_매출_정체형    -> YELLOW      원가_상승_부담형  -> YELLOW
매출_폭락형        -> RED         고금리_과다채무형 -> RED     상권_침체_붕괴형 -> RED
```

The model predicts `risk_type`; `risk_level` and the UI theme are pure lookups from it. That taxonomy is duplicated across four files with no shared constants module — **changing or adding a type means editing all of them**:

- `generate_synthetic_timeseries.py` — `CAUSE_TO_RISKTYPE` (assigns the label)
- `train_risk_model.py` — `RISKTYPE_TO_LEVEL`
- `rag_pipeline.py` — `RISK_TYPE_QUERY` and `RISK_TYPE_TO_LEVEL` (both must have every key, or `build_signal_json` raises `KeyError`)
- `rag_documents.py` — every document's `risk_type_tags`

### Label generation and the train/label circularity

In `generate_synthetic_timeseries.py`, `risk_level` is derived from `폐업률_업종내_percentile` (risk probability ∝ percentile; RED above the 0.75 quantile), and the 6-month revenue series is then generated *from* that level via `TREND_BY_LEVEL`. `train_risk_model.py` learns from the first 3 months plus that same percentile as a static feature. So reported accuracy measures recovery of the generator's own rules, not real-world predictive skill — treat metrics accordingly, and expect the RED/YELLOW subtype split (sampled from `cause_dist` / `yellow_prob`, independent of the revenue trend) to be the genuinely hard part of the classification.

Model shape: `LSTM(16)` over the `(N, 3, 1)` revenue sequence, normalized to month-1-relative values so absolute scale is discarded; concatenated with a dense branch over static features (percentile, franchise share, industry one-hots); `class_weight="balanced"` because recall on RED classes is the stated priority.

### RAG layer

`rag_pipeline.py` uses TF-IDF + cosine similarity over the 8 hardcoded documents in `rag_documents.py` — a deliberate stand-in for ko-sbert/embedding APIs, kept behind `SimpleRAGIndex.retrieve(query, risk_type, top_k)` so it can be swapped without touching callers. Retrieval filters to documents tagged with the predicted `risk_type` first, then ranks by similarity. `build_signal_json` emits the frontend contract (`risk_level`, `score`, `visual_theme`, `solutions[]`); `_similarity_score` in each solution is debug-only and marked for removal in production.

## Encoding conventions (Windows/Korean — the recurring source of bugs)

- Zip-contained Seoul CSVs are **cp949**; every generated CSV is written **utf-8-sig**.
- `sgf176_utf8.csv` has mojibake headers (`부?�사?�코??`). `generate_synthetic_timeseries.py` therefore selects the 부실사유코드 column **by position** (`sgf.columns[6]`) after a fallback loop over utf-8-sig/utf-8/cp949/euc-kr. Do not "fix" this to a name-based lookup without re-encoding the source file. (`sgf176_utf8_bom.csv` also exists but no script reads it.)
- The KOSIS xlsx has **merged cells** in `시도별(1)`, so openpyxl yields blanks for all but each region's first row. `join_kosis_hardship.py` forward-fills `last_region` to compensate — removing this silently reduces 서울특별시 to a single 전산업 row (this was a real bug).
- Column names are Korean throughout DataFrames and CSVs; keep new columns in Korean to match.
