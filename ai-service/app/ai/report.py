"""리포트 생성 (F-LLM-01). 한 번 쓰고 한 번 검사까지만 — 재생성·폴백은 10스텝 그래프가 한다."""

from collections.abc import Iterator

from openai import OpenAI

from app.core.config import OPENAI_API_KEY, OPENAI_MODEL
from app.domain.guardrail import check

SYSTEM_PROMPT = """너는 서울 소상공인에게 진단 결과와 정부 지원사업을 설명하는 상담사다.

규칙
1. 아래 <근거> 블록에 있는 정보만 쓴다. 너가 원래 알던 지원사업·금액·금리·날짜는 쓰지 않는다.
2. 금액·금리·날짜·인원 같은 숫자는 근거에 있는 값만 쓴다. 근거에 없으면 "공고문에서 확인하세요"라고 쓴다.
3. 지원사업 이름은 반드시 「」로 감싸고, 근거의 「」 안 이름을 한 글자도 바꾸지 않는다.
4. 사업장 결과는 "진단 등급"이라 부른다. "신호등"이라는 말은 쓰지 않는다.
5. 추정 원인은 확정된 원인이 아니다. "~로 추정됩니다"처럼 쓴다.
6. 모델의 정확도·성능 수치는 언급하지 않는다.

형식 (전체 600자 안팎, 마크다운 제목 없이)
- 첫 문단: 진단 등급과 추정 원인을 두세 문장으로 설명
- 지원사업마다 한 문단: 왜 이 상황에 맞는지, 한도·금리·신청기간, 어디서 신청하는지
- 마지막 문단: 이번 주에 할 일 한두 가지"""

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """첫 호출 때 만든다 — import 만으로 키 검사가 터지지 않게."""
    global _client
    if _client is None:
        if not OPENAI_MODEL:
            raise RuntimeError("OPENAI_MODEL 이 비어 있습니다. ai-service/.env 를 확인하세요.")
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def stream_report(context: str) -> Iterator[str]:
    """리포트 조각을 오는 대로 낸다. DISCLAIMER 는 호출하는 쪽이 붙인다."""
    stream = _get_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"<근거>\n{context}\n</근거>\n\n위 근거로 리포트를 써 줘."},
        ],
        temperature=0.2,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def write_report(context: str) -> tuple[str, list[str]]:
    """끝까지 받은 뒤 (본문, 가드레일 위반) 을 돌려준다."""
    text = "".join(stream_report(context))
    return text, check(text, context)


if __name__ == "__main__":
    # DB · OPENAI_MODEL 준비 후 실행. 실제 리포트 한 편과 가드레일 결과를 찍는다.
    from app.domain.report_context import DISCLAIMER, build_context
    from app.domain.signal import RISK_TYPE_QUERY
    from app.knowledge.retrieve import retrieve

    rt = "고금리_과다채무형"
    docs = [d for d, _ in retrieve(RISK_TYPE_QUERY[rt], rt)]
    signal = {"risk_level": "RED", "risk_type": rt, "risk_type_confidence": 0.61, "score": 32}
    report, bad = write_report(build_context(signal, docs))
    print(report, "\n", DISCLAIMER, "\n\n가드레일:", bad or "통과", sep="")
