"""policy_docs.json 문서 한 건의 모양

수집 경로(수동 정리 Json, P2 자동 수집기)가 무엇이든 이 모양만 맞추면 파이프라인은 그대로 돈다.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.signal import RISK_TYPE_TO_LEVEL

# DB policy_chunk.section CHECK 와 같은 목록이다. 바꾸면 마이그레이션도 같이 바꾼다.
SECTIONS = ("지원대상", "지원내용", "지원한도", "금리및조건", "신청기간", "신청방법", "제출서류", "유의사항")

class PolicySection(BaseModel):
    """
    공고문에 대한 항목 하나를 의미하며 청킹에서 조각 하나의 재료가 된다.
    name : 항목명, body : 항목 본문
    ex : PolicySection(name = "지원대상, body="2020.4~2025.6 사업 운영 개인 사업자)
    """
    model_config = ConfigDict(extra="forbid")

    name: str
    body: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def _known_section(cls, v: str) -> str:
        """항목명이 SECTIONS 안에 존재하는가. 지금은 통일된 이름만 받는다."""
        if v not in SECTIONS:
            raise ValueError(f"모르는 항목명 {v!r} - {SECTIONS} 중 하나")
        return v


class PolicyDoc(BaseModel): 
    """
    정책 공고 한 건으로 policy_doc 한행을 의미.
    """
    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(min_length=1)               # 출처+공고번호 등 변경되지 않는 값
    title: str = Field(min_length=1)                # 제도명
    agency: str = Field(min_length=1)               # 운영기관
    source_url: str = Field(pattern=r"^https?://")  # 원문 링크
    apply_start: date | None = None                 # 접수 기간 (None이면 상시 접수)
    apply_end: date | None = None
    limit_text: str | None = None
    rate_text: str | None = None
    risk_type_tags: list[str] = Field(min_length=1) # 추천할 위기 유형 최소 1개 이상
    sections: list[PolicySection] = Field(min_length=1) # 공고문 항목들

    @field_validator("risk_type_tags")
    @classmethod
    def _known_risk_type(cls, v: list[str]) -> list[str]:
        """ 태그가 6개 risk_type 안에 있는지"""
        unknown = set(v) - RISK_TYPE_TO_LEVEL.keys()
        if unknown:
            raise ValueError(f"모르는 risk_type {sorted(unknown)}")
        return v


    @model_validator(mode="after")
    def _consistent(self) -> "PolicyDoc":
        """필드 여러 개를 같이 봐야 하는 검사. 접수 기간이 거꾸로인지, 같은 항목이 두 번 나오는지"""
        if self.apply_start and self.apply_end and self.apply_start > self.apply_end:
            raise ValueError("apply_start가 end보다 늦다")
        names = [s.name for s in self.sections]
        if len(names) != len(set(names)):
            raise ValueError(f"같은 항목이 두번 나온다: {names}")
        return self