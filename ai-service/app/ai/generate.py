# Last updated: 2026-10-15
"""검색된 공고만 근거로 추천 이유를 쓰고, 규칙 가드레일로 대조

LLM 은 doc_id를 고른다. 사업명, 한도, 금리는 화면에서 DB 값으로 채운다.
"""

from openai import OpenAI
from pydantic import BaseModel

from app.core.config import OPENAI_API_KEY, OPENAI_MODEL
from app.ai.cross_check import cross_check
from app.domain.guardrail import check  

_client = OpenAI(api_key=OPENAI_API_KEY)

MAX_TRIES = 2

SYSTEM = """너는 소상공인 정부 지원사업 상담사다.
- 아래 [공고] 목록에 있는 내용만 근거로 쓴다. 목록에 없는 사업·숫자·조건은 절대 쓰지 않는다.
- 추천할 공고는 doc_id 로 고른다. 사업명을 문장에 새로 지어 쓰지 않는다.
- 금액·금리는 공고에 적힌 값만, 공고 표기 그대로 쓴다. 계산하거나 반올림하지 않는다.
- 진단 결과는 '추정'이다. 단정하지 않는다.
- reason 은 2문장 이내, 이 사업장의 위기 유형과 공고의 어느 항목이 맞는지 쓴다."""

class RecommendationRequest(BaseModel):
    doc_id: str
    reason: str


class Report(BaseModel):
    summary: str
    recommendations: list[RecommendationRequest]


def _prompt(risk_type: str, confidence: float, docs: list[dict]) -> str:
    lines = [f"[진단] 추정 위기 유형: {risk_type}, 신뢰도: {confidence:.1%}", "", "[공고]"]
    for d in docs:
        lines += [
            f"- doc_id: {d['doc_id']}",
            f"  제도명: {d['title']} / 기관: {d['agency']}",
            f"  한도: {d['limit_text'] or '공고에 없음'} / 금리: {d['rate_text'] or '공고에 없음'}",
            f"  마감: {d['apply_end'] or '상시'}",
            f"  근거: {d['evidence']}",
        ]
    return "\n".join(lines)



def _ask(risk_type: str, confidence: float, docs: list[dict]) -> Report:
    res = _client.responses.parse(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": _prompt(risk_type, confidence, docs)},
        ],
        text_format=Report,
    )
    return res.output_parsed


def _answer(report: Report) -> str:
    return " ".join([report.summary, *(r.reason for r in report.recommendations)])


def verify(report: Report, docs: list[dict]) -> list[str]:
    """가드레일에 넘길 재료를 모은다. 답변 문장 전체 vs 근거 본문·한도·금리."""
    answer = _answer(report)
    evidence = [t for d in docs for t in (d["evidence"], d["limit_text"], d["rate_text"]) if t]
    return check(answer, [r.doc_id for r in report.recommendations], evidence, {d["doc_id"] for d in docs})


def fallback(docs: list[dict]) -> Report:
    """LLM 없이 DB 값만으로 만든 리포트. 지어낼 것이 없다."""
    return Report(
        summary="진단 유형에 맞는 접수 중인 지원사업입니다. 세부 조건은 공고 원문을 확인하세요.",
        recommendations=[RecommendationRequest(doc_id=d["doc_id"], reason=f"{d['section']}: {d['evidence']}") for d in docs],
    )


def generate_report(risk_type: str, confidence: float, docs: list[dict]) -> tuple[Report, list[str]]:
    """(리포트, 마지막 위반 목록). 위반 목록이 비어 있지 않으면 템플릿으로 대체된 것이다."""
    problems: list[str] = []
    for _ in range(MAX_TRIES):
        report = _ask(risk_type, confidence, docs)
        # 규칙이 먼저다. 공짜이고, 걸리면 Claude 를 부를 필요가 없다
        problems = verify(report, docs) or cross_check(_answer(report), _prompt(risk_type, confidence, docs))
        if not problems:
            return report, []
    return fallback(docs), problems