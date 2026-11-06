from typing import Literal, TypedDict

MAX_ATTEMPTS = 2

# [TypeDict]
# LangGraph는 각 노드가 돌려준 dict를 상태에 덮어써서 합침.
# 그래서 검증 로직이 있는 Pydantic보다 가벼운 TypedDict로 충분
class ReportState(TypedDict, total=False):
    query: str                      # 검색 질의 (rist_type 별 기본 질의)
    risk_type: str                  # 진단 유형, 태그 우선 정렬
    docs: list[tuple[dict, float]]  # retrive() 결과 그대로
    context: str                    # 근거 블록 - 생성 및 가드레일, 교차검증 같은 문자열을 봄
    report: str                     # 최신 초안 리포트
    feedback: str                   # 가드레일, 교차검증 위반 -> 다음 generate에 위임
    attempts: int                   # generate 실행 횟수
    outcome: Literal["passed","regenerated","fallback","no_docs"]

