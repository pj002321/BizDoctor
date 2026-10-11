"""F-RAG-04 신호 JSON 계약 — 프론트와 맞물리는 지점. docs/스펙.md 4장을 그대로 따른다.

필드를 바꾸면 src/ 쪽 타입도 같이 바꾼다. extra="forbid" 라서 `_similarity_score` 같은
디버그 필드가 섞이면 응답 직렬화 전에 검증 오류로 막힌다.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.risk_type import RiskLevel, RiskType, VisualTheme, level_of, theme_of


class Solution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(examples=["새출발기금 (채무조정)"])
    agency: str = Field(description="소관기관")
    summary: str
    limit: str | None = Field(None, description="지원 한도. 문서에 없으면 null")
    rate: str | None = Field(None, description="금리. 문서에 없으면 null")
    url: str | None = Field(None, description="신청/안내 링크")
    source_doc_id: str = Field(description="LLM 가드레일(F-LLM-02) 대조용 원문 ID")


class SignalResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "risk_level": "RED",
                "risk_type": "고금리_과다채무형",
                "risk_type_confidence": 0.61,
                "score": 32,
                "visual_theme": "red",
                "solutions": [
                    {
                        "title": "...",
                        "agency": "...",
                        "summary": "...",
                        "limit": "...",
                        "rate": "...",
                        "url": "...",
                        "source_doc_id": "...",
                    }
                ],
            }
        },
    )

    risk_level: RiskLevel = Field(description="사업장 '진단 등급'. 상권 신호등과 다른 값이다(F-SYS-01)")
    risk_type: RiskType = Field(description="추정 원인 — 확정 진단이 아니다(F-DIA-05)")
    risk_type_confidence: float = Field(ge=0.0, le=1.0, description="risk_type 의 보정 후 확률")
    score: int = Field(ge=0, le=100, description="위험 점수(F-DIA-06)")
    visual_theme: VisualTheme
    solutions: list[Solution]

    @model_validator(mode="after")
    def _consistent(self) -> SignalResponse:
        if self.risk_level != level_of(self.risk_type):
            raise ValueError(f"risk_level {self.risk_level} 이 risk_type {self.risk_type} 와 맞지 않습니다.")
        if self.visual_theme != theme_of(self.risk_level):
            raise ValueError(f"visual_theme {self.visual_theme} 이 risk_level {self.risk_level} 와 맞지 않습니다.")
        return self
