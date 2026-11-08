"""챗봇이 도구를 골라 근거를 모으고, 그 근거로 답을 쓰는 곳.(Tool Calling)"""

from __future__ import annotations

import json
from collections.abc import Callable

from app.ai.answer import REFUSAL
from app.ai.report import _get_client
from app.core.config import OPENAI_MODEL

MAX_TOOL_ROUNDS = 3  # 도구를 이만큼 불러도 답을 못 쓰면 거절


SYSTEM_PROMPT = f"""너는 서울 소상공인 상담 챗봇이다. 지원사업·상권 질문은 반드시 도구로 근거를 찾고, 도구 결과만으로 답한다.
- 도구 결과로 답할 수 없으면 다른 말 없이 "{REFUSAL}" 한 줄만 쓴다.
- 금액·금리·날짜·조건·통계 숫자는 도구 결과 표기 그대로 쓴다. 계산하거나 바꿔 말하지 않는다.
- 지원사업 이름은 「」로 감싸고 한 글자도 바꾸지 않는다.
- "표본 적음"이 붙은 분기의 비율로 상권을 단정하지 않는다.
- 다섯 문장 이내"""

SCHEMAS = {
    "search_policy": {"type": "function", "function": {
        "name": "search_policy",
        "description": "접수 중인 정부 지원사업 공고를 찾는다. 자금·대출·금리·바우처·폐업 지원·신청 조건 질문에 쓴다.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "검색어. 질문의 핵심 단어로 짧게"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    }},
    "get_market_stats": {"type": "function", "function": {
        "name": "get_market_stats",
        "description": "사용자가 진단한 동네·업종의 최근 4개 분기 점포 수·폐업률·개업률을 가져온다. 상권·동네·경쟁 질문에 쓴다.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    }},
}



def chat(msg: str, history: list[dict], tools: dict[str, Callable[...,dict]]) -> tuple[str,str,list[dict]]:
    """질문을 도구로 근거를 모으고 답을 쓴다.
    도구를 부름 → 결과를 대화에 붙이고 다시 묻기 / 도구 안 부름 → 그게 최종 답 / 너무 많이 부름 → 거절
    반환: (답, 모은 근거 전체, 출처 목록). 근거는 다음 스텝의 검증."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *({"role": h["role"], "content": h["text"]} for h in history),
        {"role": "user", "content": msg},
    ]
    contexts, sources = [], []
    for _ in range(MAX_TOOL_ROUNDS + 1):
        msg = _get_client().chat.completions.create(
            model = OPENAI_MODEL,
            messages=messages,
            tools = [SCHEMAS[name] for name in tools],
            temperature=0,
        ).choices[0].message
        if not msg.tool_calls:
            return msg.content, "\n".join(contexts), sources
        messages.append(msg) # 도구를 이렇게 호출했다라는 기록. 이게 있어야 다음 tool 메시지가 어디에 대한 답인지 앎
        for call in msg.tool_calls:
            result = tools[call.function.name](**json.loads(call.function.arguments))
            contexts.append(result["context"])
            sources += [s for s in result.get("sources",[]) if s not in sources]
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result["context"] or "결과 없음"})
    return REFUSAL, "\n".join(contexts), sources
