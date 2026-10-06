"""임베딩 호출은 여기 한 곳에서만 한다.

문서 색인(pipeline/doc/build_index.py)과 질의 검색(retrieve)이 같은 모델,
같은 차원을 써야 벡터끼리 비교가 된다. 둘이 각자 OpenAI 를 부르면 언젠가 어긋난다.
"""

from openai import OpenAI

from app.core.config import DIMENSION, EMBED_MODEL, OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)


def embed(texts: list[str]) -> list[list[float]]:
    res = _client.embeddings.create(model=EMBED_MODEL, input=texts, dimensions=DIMENSION)
    return [d.embedding for d in res.data]
