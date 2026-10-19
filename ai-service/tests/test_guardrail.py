from datetime import date

from app.domain.guardrail import check
from app.domain.report_context import build_context, fallback_report

SIGNAL = {"risk_level": "RED", "risk_type": "고금리_과다채무형", "risk_type_confidence": 0.613, "score": 32}
DOCS = [
    {
        "doc_id": "semas-2026-refinance", "title": "2026년 소상공인 대환대출",
        "agency": "중소벤처기업부 · 소상공인시장진흥공단", "source_url": "https://ols.semas.or.kr",
        "limit_text": "기업당 최대 5,000만원(가계 1,000만원 포함)", "rate_text": "연 4.5% 고정금리",
        "apply_start": date(2026, 3, 18), "apply_end": None, "section": "지원대상",
        "evidence": "[2026년 소상공인 대환대출 · 지원대상] 상시근로자 5인 미만 소상공인으로, 연 7% 이상 고금리 대출을 보유한 자. 기존 대출이 3개월 이상 경과",
    },
    {
        "doc_id": "sbiz24-2026-stability-voucher", "title": "2026년 소상공인 경영안정 바우처",
        "agency": "중소벤처기업부 · 소상공인시장진흥공단", "source_url": "https://voucher.sbiz24.kr/",
        "limit_text": "1개사당 25만원", "rate_text": None,
        "apply_start": date(2026, 2, 9), "apply_end": date(2026, 12, 18), "section": "지원대상",
        "evidence": "[2026년 소상공인 경영안정 바우처 · 지원대상] 2025년 연 매출액이 0원 초과 1억 400만원 미만이고 비수도권은 0.2%p 인하",
    },
]
CTX = build_context(SIGNAL, DOCS)


def test_표기만_다른_값은_통과():
    report = (
        "진단 등급은 RED, 추정 확률 61%, 위험 점수 32점입니다. 「2026년 소상공인 대환대출」은 최대 5천만원까지 "
        "연 4.5%로 갈아탈 수 있습니다. 5인 미만이고 3개월이 지난 대출이 대상이며 3월 18일부터 신청합니다. "
        "「2026년 소상공인 경영안정 바우처」는 25만원이고 2026년 12월 18일 마감, 매출 1억400만 원 미만이 대상입니다."
    )
    assert check(report, CTX) == []


def test_근거에_없는_값은_모두_걸린다():
    report = "「새출발기금」으로 최대 1억원을 연 3.5%에 받을 수 있고 10인 미만이면 11월 30일까지 신청하세요. 0.2% 인하."
    assert check(report, CTX) == [
        "금액 100,000,000원", "비율 0.2%", "비율 3.5%", "날짜 11월 30일", "수치 10인", "사업명 「새출발기금」",
    ]


def test_템플릿_리포트는_항상_통과():
    assert check(fallback_report(SIGNAL, DOCS), CTX) == []
