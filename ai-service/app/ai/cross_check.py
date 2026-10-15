"""9단계 Claude 교차 검증 — 생성 모델(OpenAI)과 다른 모델이 답변을 주장 단위로 쪼개 근거를 판정한다.

규칙 가드레일은 숫자·doc_id 만 본다. "대환대출은 폐업자도 신청 가능" 처럼 숫자 없는
틀린 주장, 문장 속에 지어낸 사업명은 여기서 잡는다. 근거는 생성 모델이 본 프롬프트 그대로다.
"""

import anthropic
from pydantic import BaseModel

from app.core.config import VERIFY_MODEL

_client = anthropic.Anthropic()

SYSTEM = """너는 정부 지원사업 안내문의 사실 검증자다.
[답변]을 더 쪼갤 수 없는 주장 단위로 나누고, 각 주장이 [근거]에 명시돼 있는지 판정한다.
- 근거에 그대로 있거나 근거만으로 바로 도출되면 supported=true.
- 근거에 없거나, 근거보다 넓게 일반화했거나, 근거와 다르면 supported=false.
- 위기 유형·확률은 [진단] 줄이 근거다. '추정' 같은 완곡 표현은 판정 대상이 아니다.
- 일반 상식으로 맞는 말이어도 근거에 없으면 supported=false."""


class Claim(BaseModel):
    text: str
    supported: bool
    reason: str


class Verdict(BaseModel):
    claims: list[Claim]


def _ask(answer: str, evidence: str) -> Verdict:
    res = _client.beta.messages.parse(
        model=VERIFY_MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"[근거]\n{evidence}\n\n[답변]\n{answer}"}],
        output_format=Verdict,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # 안전 분류기가 거절하면 서버가 다른 모델로 다시 돌린다
    )
    if res.stop_reason == "refusal" or res.parsed_output is None:
        raise RuntimeError(f"교차 검증 응답 없음: {res.stop_reason}")
    return res.parsed_output


def cross_check(answer: str, evidence: str) -> list[str]:
    """근거 없는 주장 목록. 비어 있으면 통과. check() 와 같은 모양이라 그대로 이어 붙인다."""
    return [f"근거 없는 주장: {c.text} ({c.reason})" for c in _ask(answer, evidence).claims if not c.supported]
