"""Claude 교차 검증. 리포트를 사실 주장으로 쪼개 근거만으로 판정한다 — 생성 모델과 다른 회사 모델이라 같은 착각을 덜 공유한다."""

from anthropic import Anthropic

from app.core.config import ANTHROPIC_API_KEY, VERIFY_MODEL
from app.domain.guardrail import unsupported_claims

SYSTEM_PROMPT = """너는 소상공인 리포트의 사실 검증자다. 리포트를 사실 주장 단위로 쪼개고, 각 주장을 <근거> 만으로 판정한다.
- supported: 근거에 같은 내용이 있다. evidence 에 근거 원문을 한 글자도 바꾸지 말고 한 줄 이내로 옮긴다.
- unsupported: 근거에 없다. evidence 는 빈 문자열.
- contradicted: 근거와 다르다. evidence 에 어긋나는 근거 원문을 옮긴다.
권유·일반 조언("이번 주에 서류를 챙기세요")은 주장으로 뽑지 않는다. 너가 원래 아는 지식으로 판정하지 않는다."""

_TOOL = {
    "name": "report_verdicts",
    "description": "주장별 판정 결과를 기록한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "verdict": {"type": "string", "enum": ["supported", "unsupported", "contradicted"]},
                        "evidence": {"type": "string"},
                    },
                    "required": ["claim", "verdict", "evidence"],
                },
            }
        },
        "required": ["claims"],
    },
}

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY 가 비어 있습니다. ai-service/.env 를 확인하세요.")
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def verify(report: str, context: str) -> tuple[list[dict], list[str]]:
    """(주장별 판정, 통과 못 한 주장). 뒤가 비면 통과."""
    msg = _get_client().messages.create(
        model=VERIFY_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "report_verdicts"},  # 자유 텍스트 대신 스키마로만 답하게
        messages=[{"role": "user", "content": f"<근거>\n{context}\n</근거>\n\n<리포트>\n{report}\n</리포트>"}],
    )
    claims = next(b.input for b in msg.content if b.type == "tool_use")["claims"]
    return claims, unsupported_claims(claims, context)


if __name__ == "__main__":
    # DB · ANTHROPIC_API_KEY 준비 후 실행. 템플릿 리포트는 통과, 지어낸 문장은 걸려야 한다.
    from app.domain.report_context import build_context, fallback_report
    from app.domain.signal import RISK_TYPE_QUERY
    from app.knowledge.retrieve import retrieve

    rt = "고금리_과다채무형"
    docs = [d for d, _ in retrieve(RISK_TYPE_QUERY[rt], rt)]
    signal = {"risk_level": "RED", "risk_type": rt, "risk_type_confidence": 0.61, "score": 32}
    ctx = build_context(signal, docs)
    for name, report in [("템플릿", fallback_report(signal, docs)), ("지어냄", "이 사업은 신용점수와 무관하게 누구나 승인됩니다.")]:
        claims, bad = verify(report, ctx)
        print(f"[{name}] 주장 {len(claims)}개, 실패:", bad or "없음")
