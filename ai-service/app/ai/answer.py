from app.ai.report import _get_client
from app.core.config import OPENAI_MODEL

REFUSAL = "해당하는 접수 중 공고가 없습니다."

SYSTEM_PROMPT = f"""너는 소상공인 정부 지원사업 상담사다. <근거> 에 있는 내용만으로 질문에 답한다.
- 근거로 답할 수 없으면 다른 말 없이 "{REFUSAL}" 한 줄만 쓴다.
비슷한 다른 사업을 대신 권하지 않는다.
- 금액,금리,날짜,조건은 근거 표기 그대로 쓴다. 계산하거나 바꿔 말하지 않는다.
- 지원사업 이름은 「」로 감싸고 근거의 이름을 한 글자도 바꾸지 않는다.
- 세 문장 이내"""


def answer(question: str, context: str) -> str:
    res = _get_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"<근거>\n{context}\n</근거>\n\n질문: {question}"},
        ],
        temperature=0,  # 같은 질문엔 같은 답
    )
    return res.choices[0].message.content