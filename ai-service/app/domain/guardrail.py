# Last updated: 2026-10-15
"""규칙 가드레일 - 답변의 금액,비율,사업명이 검색 근거에 있는지 대조한다.

근거에 없는 숫자는 LLM이 지어낸 것으로 본다. 같은 값도 표기가 여러 가지라서
숫자와 단위를 분리하여 비교한다. 예를 들어, 1억 2천만원은 1억 2천만 원, 1억2천만원, 1억2천만 원 등으로 표기될 수 있다. 
따라서 숫자와 단위를 분리하여 비교한다.

사업명은 문자열로 대조하지 않는다. LLM 은 사업명 대신 doc_id 를 고르고(구조화 출력),
화면의 사업명은 DB 에서 채운다. 그래서 doc_id 가 검색 결과 안에 있는지만 본다.
자유 문장 속에 지어낸 사업명은 9단계 Claude 교차 검증이 잡는다.
"""

from __future__ import annotations

import re
from decimal import Decimal

SMALL = {"천": 1000, "백": 100, "십": 10}
BIG = {"조": 1000000000000, "억": 100000000, "만": 10000}

MONEY = re.compile(r"(?:\d[\d,]*(?:\.\d+)?\s*[조억만천백십]*\s*)+원")
TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?|[조억만천백십]")
RATE = re.compile(r"(\d+(?:\.\d+)?)\s*(%p|%포인트|%)")

def _won(expr: str) -> Decimal:
    """금액 문자열을 Decimal로 변환한다."""
    total = group = Decimal(0)
    cur: Decimal | None = None
    for token in TOKEN.findall(expr):
        if token in SMALL:
            group += (cur or 1) * SMALL[token]
            cur = None
        elif token in BIG:
            total += (group + (cur or 0) or 1) * BIG[token]
            group, cur = Decimal(0), None
        else:
            cur = Decimal(token.replace(",", ""))
    return total + group + (cur or 0)


def extract_numbers(text: str) -> set[tuple[str, Decimal]]:
    """금액은 ("원", 원 단위), 비율은 ("%", 값) · ("%p", 값). 0.2% 와 0.2%p 는 다른 값이다."""
    found = {("원", _won(m)) for m in MONEY.findall(text)}
    found |= {("%p" if unit != "%" else "%", Decimal(v)) for v, unit in RATE.findall(text)}
    return found


def check(answer: str, cited_ids: list[str], evidence: list[str], allowed_ids: set[str]) -> list[str]:
    """위반 메시지 목록. 비어 있으면 통과. evidence 에는 조각 본문과 limit_text·rate_text 를 넣는다."""
    known = set().union(*(extract_numbers(e) for e in evidence))
    problems = [f"근거에 없는 숫자: {v.normalize():f}{unit}" for unit, v in sorted(extract_numbers(answer) - known)]
    problems += [f"검색 결과에 없는 문서: {d}" for d in cited_ids if d not in allowed_ids]
    return problems