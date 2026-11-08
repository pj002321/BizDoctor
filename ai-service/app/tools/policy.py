"""챗봇,MCP가 같이 쓰는 공고 검색 도구."""
from __future__ import annotations

from app.domain.report_context import docs_context
from app.knowledge.retrieve import retrieve


def search_policy(query: str, risk_type: str|None=None, top_k: int =3) -> dict:
    """공고 서류철에서 질문에 맞는 공고를 찾아 온다.
    LLM에게 줄 근거(context) + 화면에 보여 줄 출처(sources)를 한 번에 돌려줌
    0건이라면 둘다 비어 있음"""
    docs = [d for d,_ in retrieve(query,risk_type,top_k)]
    return {
        "context": docs_context(docs),
        "sources": [{"docId": d["doc_id"], "title": d["title"]} for d in docs],
    }
