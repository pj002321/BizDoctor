"""분기 표기 변환. API 는 '2025Q4', DB(기준_년분기_코드 원본)는 '20254'.

DB 쪽 형식이 바뀌면 이 파일만 고친다.
"""
from __future__ import annotations

import re

API_QUARTER_PATTERN = r"^\d{4}Q[1-4]$"
_API_RE = re.compile(API_QUARTER_PATTERN)
_DB_RE = re.compile(r"^(\d{4})([1-4])$")


def api_to_db(q: str) -> str:
    if not _API_RE.match(q):
        raise ValueError(f"분기 형식은 YYYYQn 입니다: {q!r}")
    return q[:4] + q[5]


def db_to_api(q: str | int) -> str:
    m = _DB_RE.match(str(q))
    if not m:
        raise ValueError(f"DB 분기 코드 형식이 아닙니다: {q!r}")
    return f"{m.group(1)}Q{m.group(2)}"
