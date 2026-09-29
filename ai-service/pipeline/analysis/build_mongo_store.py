# -*- coding: utf-8 -*-
"""
상권 신호등 - MongoDB 문서 저장소 구축

설계 근거 — 무엇을 SQL에 두고 무엇을 NoSQL에 두는가:

  정형 패널(행정동x업종x분기)은 스키마가 고정이고 집계·윈도우 연산이 핵심이라
  관계형(SQLite)이 맞다. 반면 아래 3종은 관계형에 넣으면 손해가 크다.

    policy_documents  지원제도 원문. 길이가 제각각이고 risk_type 태그가
                      가변 길이 배열이다. 관계형이면 별도 태그 테이블 + 조인이
                      필요하지만 문서 모델은 배열을 그대로 담고 색인한다.

    risk_signals      사업자별 신호 JSON. visual_theme(중첩 객체)와
                      solutions(0~N개 배열)를 포함한다. 관계형이면 3개 테이블로
                      쪼개야 하는 구조가 문서 하나로 끝난다.

    model_runs        실험 이력. 실험마다 기록하는 하이퍼파라미터가 달라져
                      스키마가 계속 바뀐다. 스키마리스가 유리한 전형적 사례.

실행 전 준비 (둘 중 하나):
  A) 로컬  : MongoDB Community Server 설치 후 기본 포트(27017)로 기동
  B) 클라우드: MongoDB Atlas 무료 티어(M0) 생성 후 연결 문자열을 환경변수로 지정
             set MONGO_URI=mongodb+srv://<user>:<pw>@<cluster>.mongodb.net/

실행: python build_mongo_store.py
"""
import os
import sys
from datetime import datetime, timezone

import pandas as pd
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import ServerSelectionTimeoutError

from rag_documents import DOCUMENTS
from rag_pipeline import SimpleRAGIndex, build_signal_json, RISK_TYPE_TO_LEVEL

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "shinhan_signal"

# ------------------------------------------------------------------
# 0. 연결
# ------------------------------------------------------------------
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
try:
    info = client.server_info()
except ServerSelectionTimeoutError:
    sys.exit(
        "MongoDB에 연결하지 못했습니다.\n"
        f"  시도한 주소: {MONGO_URI}\n"
        "  로컬 서버를 켜거나, MONGO_URI 환경변수에 Atlas 연결 문자열을 지정하세요."
    )

db = client[DB_NAME]
print(f"MongoDB {info['version']} 연결 → DB '{DB_NAME}'")

# ------------------------------------------------------------------
# 1. policy_documents — 지원제도 원문 (가변 길이 태그 배열)
# ------------------------------------------------------------------
db.policy_documents.drop()
db.policy_documents.insert_many([
    {
        "_id": d["doc_id"],
        "title": d["title"],
        "content": d["content"],
        "risk_type_tags": d["risk_type_tags"],      # 가변 길이 배열
        "char_len": len(d["content"]),
        "source_year": 2026,
        "ingested_at": datetime.now(timezone.utc),
    }
    for d in DOCUMENTS
])
db.policy_documents.create_index([("risk_type_tags", ASCENDING)])
db.policy_documents.create_index([("title", TEXT), ("content", TEXT)])
print(f"  policy_documents  {db.policy_documents.count_documents({}):>6,}건  "
      f"(태그 배열 색인 + 텍스트 색인)")

# ------------------------------------------------------------------
# 2. risk_signals — 사업자별 신호 JSON (중첩 객체 + 가변 배열)
# ------------------------------------------------------------------
companies = pd.read_csv("synthetic_companies.csv")
index = SimpleRAGIndex(DOCUMENTS)

db.risk_signals.drop()
BATCH, buf = 2000, []
for row in companies.itertuples(index=False):
    doc = build_signal_json(row.company_id, row.risk_type, row.score, index)
    doc["_id"] = doc.pop("company_id")
    doc["location"] = {"행정동": row.행정동_코드_명, "업종": row.서비스_업종_코드_명,
                       "산업대분류": row.KOSIS_산업1}
    doc["generated_at"] = datetime.now(timezone.utc)
    buf.append(doc)
    if len(buf) >= BATCH:
        db.risk_signals.insert_many(buf); buf = []
if buf:
    db.risk_signals.insert_many(buf)

db.risk_signals.create_index([("risk_level", ASCENDING), ("score", DESCENDING)])
db.risk_signals.create_index([("risk_type", ASCENDING)])
db.risk_signals.create_index([("location.산업대분류", ASCENDING)])
print(f"  risk_signals      {db.risk_signals.count_documents({}):>6,}건  "
      f"(중첩 객체 + solutions 배열)")

# ------------------------------------------------------------------
# 3. model_runs — 실험 이력 (스키마가 실험마다 달라지는 컬렉션)
# ------------------------------------------------------------------
db.model_runs.drop()
db.model_runs.insert_many([
    {
        "run": "01_buggy_encoding",
        "note": "부실사유 인코딩 손실로 RED가 1개 유형으로 붕괴",
        "n_companies": 3000, "n_classes": 4,
        "metrics": {"type_accuracy": 0.622, "level_accuracy": 0.650,
                    "red_recall": 1.000, "yellow_recall": 0.788},
    },
    {
        "run": "02_encoding_fixed",
        "note": "인코딩 수정 후 6클래스. class_weight=balanced 유지",
        "n_companies": 3000, "n_classes": 6,
        "class_weight": "balanced", "max_weight_ratio": 228.4,
        "metrics": {"type_accuracy": 0.213, "level_accuracy": 0.262,
                    "red_recall": 0.853, "yellow_recall": 0.865},
    },
    {
        "run": "03_no_class_weight",
        "note": "가중치 제거. 정확도는 올랐으나 YELLOW가 소멸",
        "n_companies": 3000, "n_classes": 6, "class_weight": None,
        "metrics": {"type_accuracy": 0.878, "level_accuracy": 0.898,
                    "red_recall": 0.765, "yellow_recall": 0.000},
    },
    {
        "run": "04_resampled",
        "note": "표본 30,000곳 + 위험군 과표집으로 불균형 해소",
        "n_companies": 30000, "n_classes": 6, "class_weight": None,
        "base_risk_rate": 0.30, "min_class_train": 293,
        "metrics": {"type_accuracy": 0.755, "level_accuracy": 0.838,
                    "red_recall": 0.933, "red_precision": 0.985,
                    "yellow_recall": 0.339, "majority_baseline": 0.658},
    },
])
db.model_runs.create_index([("run", ASCENDING)], unique=True)
print(f"  model_runs        {db.model_runs.count_documents({}):>6,}건  (스키마리스 실험 이력)")

print(f"\n완료 — mongosh 로 확인: use {DB_NAME}; db.risk_signals.findOne()")
client.close()
