"""
golden.py
- 정답 공고를 제대로 찾는지 -
검색 엔진 채점 시험지(golden.jsonl)과 정답 양식(GoldItem)

정답 doc_id 오타는 오류 없이 hit@3 를 0 으로 만듦으로 읽을 때 
policy_docs.json 과 대조한다."""


import json
from pathlib import Path
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.core import config
from app.domain.signal import RISK_TYPE_TO_LEVEL

GOLDEN = Path(__file__).parent / "golden.jsonl";
POLICY_DOCS = config.DATA_DIR/"raw"/"policy_docs.json"

AS_OF = date(2026,10,30)
NO_ANSWER = ("마감_함정", "범위_밖")

QuestionType = Literal["위기_유형", "조건", "수치", *NO_ANSWER]

class GoldFact(BaseModel):
    """답에 반드시 들어가야 할 사실 하나와 그 출처 항목"""
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    section: str
    value: str

class GoldItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: QuestionType
    question: str
    risk_type: str | None = None
    gold_doc_ids: list[str] = []
    gold_facts: list[GoldFact] = []

    @model_validator(mode="after") # decorator
    def _consistent(self):
        if self.risk_type is not None and self.risk_type not in RISK_TYPE_TO_LEVEL:
            raise ValueError(f"모르는 risk_type {self.risk_type!r}"); # !r : 을 코드에 적는 모양 그대로
        # 값을 변수에 담으면서 동시에 그 값을 조건으로 
        if (self.type in NO_ANSWER) == bool(self.gold_doc_ids):
            raise ValueError(f"{self.type} 은 gold_doc_ids 가 {'비어야' if self.type in NO_ANSWER else '있어야'} 한다")
        if stray := {f.doc_id for f in self.gold_facts} - set(self.gold_doc_ids):
            raise ValueError(f"gold_facts의 doc_id {sorted(stray)} 가 gold_doc_ids 에 없다.")

        return self

    
def load_golden(path: Path = GOLDEN) -> list[GoldItem]:
    """시험지를 한 줄씩 읽어 양식에 맞는지 검사 후 통과한 문제만 반환"""
    docs = {d["doc_id"]: d for d in json.loads(POLICY_DOCS.read_text(encoding="utf-8"))}
    items = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = GoldItem.model_validate_json(line)
        if unknown := set(item.gold_doc_ids) - docs.keys():
            raise ValueError(f"{path.name}:{n} 없는 doc_id {sorted(unknown)}")
        # 마감된 공고는 검색에서 빠지므로 정답이 될 수 없다. retrieve.py 의 apply_end >= 오늘 을 뒤집은 조건.
        if expired := [d for d in item.gold_doc_ids
                       if docs[d]["apply_end"] and date.fromisoformat(docs[d]["apply_end"]) < AS_OF]:
            raise ValueError(f"{path.name}:{n} {AS_OF} 기준 마감된 정답 {expired} — 질문을 바꾸거나 마감_함정으로 옮긴다")
        items.append(item)
    if len({i.id for i in items}) != len(items):
        raise ValueError("id 중복")
    return items


if __name__ == "__main__":
    # 질문마다 정답 공고 제목과 정답 사실을 보여 준다. 엉뚱한 공고나 원문에 없는 값은 눈으로 잡힌다.
    docs = {d["doc_id"]: d for d in json.loads(POLICY_DOCS.read_text(encoding="utf-8"))}
    for item in load_golden():
        print(f"[{item.id} · {item.type}] {item.question}")
        for doc_id in item.gold_doc_ids:
            print(f"  → {docs[doc_id]['title']} (마감 {docs[doc_id]['apply_end'] or '상시'})")
        for f in item.gold_facts:
            body = next((s["body"] for s in docs[f.doc_id]["sections"] if s["name"] == f.section), "")
            print(f"    {'✓' if f.value in body else '✗ 원문에 없음'} {f.section}: {f.value}")
        if not item.gold_doc_ids:
            print("  → 정답 없음 (검색 0건 · 거절이 정답)")