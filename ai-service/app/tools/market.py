"""챗봇,MCP가 같이 쓰는 상권 지표 도구."""

# 상담 창구 직원(챗봇) 옆에 통계 자료실이 있다고 비유. 
# 직원은 표 12장을 다 들고 올 수 없으니, 자료실 담당자(get_market_stats)에게
# "망원1동 카페 거 최근 1년치만 한 장으로 요약해 주세요"라고 부탁

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.market_signal import top_percent
from app.schemas.common import MarketFilter
from app.service import market_service

RECENT = 4 # 최근 1년치 분기


# 챗봇이 "우리 동네 상권 어때요?"라는 질문을 받았을 때 꺼내 보는 상권 통계 요약 쪽지를 만드는 함수
def get_market_stats(db: Session, district_code: str, industry_code: str) -> dict:
    """그 동네,업종의 최근 상권 지표를 찾아옴.
    점포 5개 이하 분기 -> "표본적음"표시 / 마지막 분기에만 업종 내 위험 순위를 붙임"""
    cell = market_service.get_cells(db, district_code, MarketFilter(industry_code = industry_code))
    points = cell.points[-RECENT:]
    lines = [f"[상권] {cell.district_name} {cell.industry_name} (최근 {len(points)}개 분기)"]
    for p in points:
        line = f"{p.quarter}: 점포 {p.store_count}개 · 폐업률 {p.closure_rate}% · 개업률 {p.open_rate}%"

        if p.small_sample:
            line += " · 표본 적음(점포 5개 이하라 비율이 크게 튐)"
        lines.append(line)
    last = points[-1] if points else None
    if last and last.closure_pctl_in_industry is not None:
        lines[-1] += f" · 업종 내 폐업 위험 상위 {top_percent(last.closure_pctl_in_industry)}%"
    return {"context": "\n".join(lines)}

