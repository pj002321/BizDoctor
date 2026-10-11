# [역할] 신호 JSON 계약 — 프론트로 나가는 risk_level·risk_type·score·visual_theme·solutions[] 형태를 고정한다 (F-RAG-04).
"""F-RAG-04 신호 JSON 계약 — 프론트와 맞물리는 지점. docs/스펙.md 4장을 그대로 따른다.

필드를 바꾸면 src/ 쪽 타입도 같이 바꾼다. extra="forbid" 라서 `_similarity_score` 같은
디버그 필드가 섞이면 응답 직렬화 전에 검증 오류로 막힌다.
"""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 스키마 기반 클래스·설정·필드 옵션·모델 단위 검증.
from pydantic import BaseModel, ConfigDict, Field, model_validator

# 유형·등급·테마 타입과, 유형→등급·등급→테마 변환 함수.
from app.domain.risk_type import RiskLevel, RiskType, VisualTheme, level_of, theme_of


# 추천 정책자금 한 건.
class Solution(BaseModel):
    # 정의 안 된 필드(예: _similarity_score)가 들어오면 오류.
    model_config = ConfigDict(extra="forbid")

    # 지원사업 이름
    title: str = Field(examples=["새출발기금 (채무조정)"])
    # 소관기관
    agency: str = Field(description="소관기관")
    # 요약 설명
    summary: str
    # 지원 한도(없으면 null)
    limit: str | None = Field(None, description="지원 한도. 문서에 없으면 null")
    # 금리(없으면 null)
    rate: str | None = Field(None, description="금리. 문서에 없으면 null")
    # 신청·안내 링크(없으면 null)
    url: str | None = Field(None, description="신청/안내 링크")
    # 원문 문서 ID — LLM 리포트 수치 대조에 쓴다.
    source_doc_id: str = Field(description="LLM 가드레일(F-LLM-02) 대조용 원문 ID")


# POST /api/diagnosis 응답 본문 전체.
class SignalResponse(BaseModel):
    # 모델 설정
    model_config = ConfigDict(
        # 정의 안 된 필드 금지
        extra="forbid",
        # OpenAPI 문서에 보일 예시 — 프론트가 목업으로 쓸 수 있다.
        json_schema_extra={
            # 예시 본문
            "example": {
                # 진단 등급
                "risk_level": "RED",
                # 추정 원인 유형
                "risk_type": "고금리_과다채무형",
                # 유형 확률
                "risk_type_confidence": 0.61,
                # 위험 점수
                "score": 32,
                # 화면 테마
                "visual_theme": "red",
                # 추천 정책자금 목록
                "solutions": [
                    # 한 건 예시(값은 자리표시자)
                    {
                        # 이름
                        "title": "...",
                        # 기관
                        "agency": "...",
                        # 요약
                        "summary": "...",
                        # 한도
                        "limit": "...",
                        # 금리
                        "rate": "...",
                        # 링크
                        "url": "...",
                        # 원문 ID
                        "source_doc_id": "...",
                    }
                ],
            }
        },
    )

    # 사업장 진단 등급(GREEN/YELLOW/RED)
    risk_level: RiskLevel = Field(description="사업장 '진단 등급'. 상권 신호등과 다른 값이다(F-SYS-01)")
    # 6개 중 하나의 추정 원인
    risk_type: RiskType = Field(description="추정 원인 — 확정 진단이 아니다(F-DIA-05)")
    # 그 유형의 확률(0~1)
    risk_type_confidence: float = Field(ge=0.0, le=1.0, description="risk_type 의 보정 후 확률")
    # 위험 점수(0~100 정수)
    score: int = Field(ge=0, le=100, description="위험 점수(F-DIA-06)")
    # 화면 테마(green/yellow/red)
    visual_theme: VisualTheme
    # 추천 정책자금 목록
    solutions: list[Solution]

    # 필드 검증이 끝난 뒤 세 값이 서로 맞는지 확인한다.
    @model_validator(mode="after")
    def _consistent(self) -> SignalResponse:
        # risk_level · visual_theme 은 risk_type 에서 표로 정해진다. 따로 놀면 계약 위반.
        if self.risk_level != level_of(self.risk_type):
            # 등급이 유형과 안 맞으면 오류.
            raise ValueError(f"risk_level {self.risk_level} 이 risk_type {self.risk_type} 와 맞지 않습니다.")
        # 테마가 등급과 안 맞으면
        if self.visual_theme != theme_of(self.risk_level):
            # 오류.
            raise ValueError(f"visual_theme {self.visual_theme} 이 risk_level {self.risk_level} 와 맞지 않습니다.")
        # 문제없으면 자기 자신을 돌려준다.
        return self
