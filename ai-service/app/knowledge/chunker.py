"""정책 문서 -> 검색 조각. DB도 모델도 안 쓰는 순수 함수라 테스트만 확인한다.

섹션(항목) 하나가 기본 조각이며, MAX_TOKENS를 넘는 항목만 문장 경계에서 나눔.
토큰으로 자르지 않는 이유는 한글이 두 코큰에 걸치면 디코딩 결과가 깨진다.
"""

import re

import tiktoken

from app.core.config import EMBED_MAX_TOKENS, EMBED_TOKENIZER
from app.schemas.policy_doc import PolicyDoc

MAX_TOKENS = 512
assert MAX_TOKENS <= EMBED_MAX_TOKENS

_enc = tiktoken.get_encoding(EMBED_TOKENIZER)

_SENTENCE_END = re.compile(r"\n+|(?<=[.!?])\s+")


def count_tokens(text: str) -> int:
    """임베딩 모델 토크나이저로 센 토큰 수"""

    return len(_enc.encode(text))


def split_section(header: str, body: str) -> list[str]:
    """항목 본문 하나를 MAX_TOKENS이하 조각들로 나눈다. 
    조각마다 머리말을 붙히기 때문에 조각만으로 어느 제도의 어느 항목인지 알 수 있다."""

    whole = f"{header} {body}"
    if count_tokens(whole) <= MAX_TOKENS:
        return [whole]

    pieces, current = [], header
    for sentence in filter(None, (s.strip() for s in _SENTENCE_END.split(body))):
        if count_tokens(f"{header} {sentence}") > MAX_TOKENS:
            raise ValueError(f"{header} 문장 하나가 {MAX_TOKENS} 토큰을 넘는다: {sentence[:40]}...")
        candidate = f"{current} {sentence}"
        if count_tokens(candidate) > MAX_TOKENS:
            pieces.append(current)
            candidate = f"{header} {sentence}"
        current = candidate

    pieces.append(current)
    return pieces


def chunk_doc(doc: PolicyDoc) -> list[dict]:
    """문서 한 건을 polict_chunk 행 목록으로 만든다. chunk_index는 항목 순서대로 0부터 이어짐
    doc은 검증을 통과한 공고문이며, INSERT에 넘긴다."""

    rows = []
    for section in doc.sections:
        for body in split_section(f"[{doc.title} · {section.name}]", section.body):
            rows.append({
                "doc_id": doc.doc_id,
                "chunk_index": len(rows),
                "section": section.name,
                "body": body,
                "n_tokens": count_tokens(body)
            })
    return rows

