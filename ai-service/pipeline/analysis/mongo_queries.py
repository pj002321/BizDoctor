# -*- coding: utf-8 -*-
"""
상권 신호등 - MongoDB 집계 쿼리

build_mongo_store.py 로 적재한 문서 저장소에 대해,
관계형에서는 번거로운 연산을 aggregation pipeline 으로 수행한다.

핵심 대비:
  SQL 이었다면 solutions 를 별도 테이블로 분리하고 JOIN 해야 할 것을
  $unwind 한 줄로 펼친다. 태그 배열 검색도 $in 하나로 끝난다.

실행: python mongo_queries.py
"""
import os
import sys

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
try:
    client.server_info()
except ServerSelectionTimeoutError:
    sys.exit(f"MongoDB 연결 실패: {MONGO_URI}\nbuild_mongo_store.py 안내를 참고하세요.")

db = client["shinhan_signal"]


def show(title, rows, cols):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    if not rows:
        print("  (결과 없음)")
        return
    widths = [max(len(str(c)), max(len(str(r.get(c, ""))) for r in rows)) for c in cols]
    print("  " + "  ".join(str(c).ljust(w) for c, w in zip(cols, widths)))
    print("  " + "  ".join("-" * w for w in widths))
    for r in rows:
        print("  " + "  ".join(str(r.get(c, "")).ljust(w) for c, w in zip(cols, widths)))


# ------------------------------------------------------------------
# 1. 위험 유형별 신호 분포 — $group
# ------------------------------------------------------------------
rows = list(db.risk_signals.aggregate([
    {"$group": {
        "_id": {"level": "$risk_level", "type": "$risk_type"},
        "건수": {"$sum": 1},
        "평균점수": {"$avg": "$score"},
        "제안수": {"$avg": {"$size": "$solutions"}},
    }},
    {"$project": {
        "_id": 0,
        "등급": "$_id.level", "유형": "$_id.type", "건수": 1,
        "평균점수": {"$round": ["$평균점수", 1]},
        "평균제안수": {"$round": ["$제안수", 1]},
    }},
    {"$sort": {"건수": -1}},
]))
show("[1] 위험 등급·유형별 신호 분포", rows, ["등급", "유형", "건수", "평균점수", "평균제안수"])

# ------------------------------------------------------------------
# 2. 어떤 지원제도가 가장 많이 추천되는가 — $unwind
#    (관계형이면 solutions 테이블 분리 + JOIN 이 필요한 연산)
# ------------------------------------------------------------------
rows = list(db.risk_signals.aggregate([
    {"$unwind": "$solutions"},
    {"$group": {
        "_id": "$solutions.title",
        "추천횟수": {"$sum": 1},
        "평균유사도": {"$avg": "$solutions._similarity_score"},
    }},
    {"$project": {
        "_id": 0, "지원제도": "$_id", "추천횟수": 1,
        "평균유사도": {"$round": ["$평균유사도", 3]},
    }},
    {"$sort": {"추천횟수": -1}},
]))
show("[2] 지원제도별 추천 횟수 ($unwind 로 배열 전개)", rows,
     ["지원제도", "추천횟수", "평균유사도"])

# ------------------------------------------------------------------
# 3. 산업대분류별 RED 비중 — 중첩 필드 기준 집계
# ------------------------------------------------------------------
rows = list(db.risk_signals.aggregate([
    {"$group": {
        "_id": "$location.산업대분류",
        "전체": {"$sum": 1},
        "RED": {"$sum": {"$cond": [{"$eq": ["$risk_level", "RED"]}, 1, 0]}},
    }},
    {"$project": {
        "_id": 0, "산업대분류": "$_id", "전체": 1, "RED": 1,
        "RED비중_pct": {"$round": [{"$multiply": [{"$divide": ["$RED", "$전체"]}, 100]}, 2]},
    }},
    {"$sort": {"RED비중_pct": -1}},
    {"$limit": 8},
]))
show("[3] 산업대분류별 RED 비중 (중첩 필드 location.산업대분류)", rows,
     ["산업대분류", "전체", "RED", "RED비중_pct"])

# ------------------------------------------------------------------
# 4. 태그 배열 검색 — $in (관계형이면 태그 테이블 + JOIN)
# ------------------------------------------------------------------
target = "고금리_과다채무형"
rows = [{"제도": d["title"], "태그수": len(d["risk_type_tags"]), "길이": d["char_len"]}
        for d in db.policy_documents.find(
            {"risk_type_tags": target}, {"title": 1, "risk_type_tags": 1, "char_len": 1})]
show(f"[4] '{target}' 태그가 붙은 지원제도 ($in 배열 검색)", rows, ["제도", "태그수", "길이"])

# ------------------------------------------------------------------
# 5. 실험 이력 — 스키마가 서로 다른 문서를 한 컬렉션에서 조회
# ------------------------------------------------------------------
rows = [{
    "실험": d["run"],
    "표본": f"{d['n_companies']:,}",
    "클래스": d["n_classes"],
    "등급정확도": d["metrics"].get("level_accuracy"),
    "RED재현율": d["metrics"].get("red_recall"),
    "YELLOW재현율": d["metrics"].get("yellow_recall"),
} for d in db.model_runs.find().sort("run", 1)]
show("[5] 실험 이력 (문서마다 필드 구성이 다름 — 스키마리스)", rows,
     ["실험", "표본", "클래스", "등급정확도", "RED재현율", "YELLOW재현율"])

print("\n" + "=" * 70)
print("설계 요약")
print("=" * 70)
print("  정형 패널 387,266행 → SQLite  (윈도우 함수로 시계열 피처·상대순위)")
print("  비정형 문서·신호·이력      → MongoDB (가변 배열·중첩 객체·스키마 진화)")
print("  두 저장소는 KOSIS_산업1 과 company_id 로 논리적으로 연결된다.")

client.close()
