"""리포트 근거 텍스트와 템플릿 리포트. LLM 에 준 근거와 가드레일 대조 근거가 같도록 build_context 한 곳에서만 만든다."""

# LLM 이 아니라 코드가 붙인다 (F-LLM-05 · F-SYS-08)
DISCLAIMER = (
    "※ 이 진단은 공개 상권 통계와 시뮬레이션으로 학습한 모델의 추정이며, 실제 매출·채무 자료로 검증된 결과가 아닙니다. "
    "지원사업의 한도·금리·기간은 반드시 공고 원문에서 확인하세요."
)


def _period(doc: dict) -> str:
    start, end = doc.get("apply_start"), doc.get("apply_end")
    if start and end:
        return f"{start} ~ {end}"
    if start:
        return f"{start}부터 (마감일 공고 없음)"
    return "상시 (공고 확인)"


def build_context(signal: dict, docs: list[dict]) -> str:
    """신호 JSON + retrieve() 공고 → LLM 근거 텍스트. 확률은 여기서 % 로 바꿔 둔다."""
    lines = [
        "[진단]",
        f"진단 등급: {signal['risk_level']}",
        f"추정 원인: {signal['risk_type']} (추정 확률 {round(signal['risk_type_confidence'] * 100)}%)",
        f"위험 점수: {signal['score']}점",
    ]
    for i, d in enumerate(docs, 1):
        lines += [
            "",
            f"[근거 {i}] 「{d['title']}」",
            f"운영기관: {d['agency']}",
            f"지원한도: {d.get('limit_text') or '공고문 확인'}",
            f"금리: {d.get('rate_text') or '해당 없음'}",
            f"신청기간: {_period(d)}",
            f"링크: {d['source_url']}",
            f"근거 항목({d['section']}): {d['evidence']}",
        ]
    return "\n".join(lines)


def fallback_report(signal: dict, docs: list[dict]) -> str:
    """가드레일 재실패 시 템플릿. 근거 필드를 그대로 옮기므로 항상 통과한다."""
    lines = [
        f"진단 등급은 {signal['risk_level']}, 추정 원인은 {signal['risk_type']}"
        f"(추정 확률 {round(signal['risk_type_confidence'] * 100)}%)입니다. 위험 점수는 {signal['score']}점입니다.",
        "",
        "확인해 볼 지원사업:",
    ]
    for d in docs:
        lines.append(
            f"- 「{d['title']}」({d['agency']}) · 한도 {d.get('limit_text') or '공고문 확인'}"
            f" · 금리 {d.get('rate_text') or '해당 없음'} · 신청기간 {_period(d)} · {d['source_url']}"
        )
    lines += ["", DISCLAIMER]
    return "\n".join(lines)
