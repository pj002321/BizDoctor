# [역할] 분기 표기 변환 — API 형식 '2025Q4' ↔ DB 형식 '20254' 를 서로 바꾼다.
"""분기 표기 변환. API 는 '2025Q4', DB(기준_년분기_코드 원본)는 '20254'.

DB 쪽 형식이 바뀌면 이 파일만 고친다.
"""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 정규표현식으로 형식을 검사하기 위해 가져온다.
import re

# API 분기 형식 패턴: 연도 4자리 + 'Q' + 1~4. 스키마의 Query 검증에도 재사용한다.
API_QUARTER_PATTERN = r"^\d{4}Q[1-4]$"
# 위 패턴을 미리 컴파일해 둔다.
_API_RE = re.compile(API_QUARTER_PATTERN)
# DB 분기 형식 패턴: 연도 4자리 + 분기 1자리(예: 20254). 괄호로 연도·분기를 따로 잡는다.
_DB_RE = re.compile(r"^(\d{4})([1-4])$")


# '2025Q4' → '20254'
def api_to_db(q: str) -> str:
    # API 형식이 아니면
    if not _API_RE.match(q):
        # 잘못된 값이라고 알린다.
        raise ValueError(f"분기 형식은 YYYYQn 입니다: {q!r}")
    # 앞 4글자(연도) + 6번째 글자(분기 숫자)를 이어 붙인다.
    return q[:4] + q[5]


# '20254'(또는 정수 20254) → '2025Q4'
def db_to_api(q: str | int) -> str:
    # 문자열로 바꾼 뒤 DB 형식에 맞는지 확인한다.
    m = _DB_RE.match(str(q))
    # 맞지 않으면
    if not m:
        # 잘못된 값이라고 알린다.
        raise ValueError(f"DB 분기 코드 형식이 아닙니다: {q!r}")
    # 잡아낸 연도와 분기 사이에 'Q' 를 넣어 돌려준다.
    return f"{m.group(1)}Q{m.group(2)}"
