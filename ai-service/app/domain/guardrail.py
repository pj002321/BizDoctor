"""리포트의 금액·비율·날짜·수치·「사업명」이 근거에 있는지 대조한다 (F-LLM-02). 표기만 다른 같은 값은 통과."""

import re

_UNITS = {"억": 10**8, "천만": 10**7, "백만": 10**6, "만": 10**4, "천": 10**3}

_MONEY = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:억|천만|백만|만|천)?(?:\s*\d[\d,]*\s*(?:천만|백만|만|천))*\s*원")  # "1억 400만원"
_MONEY_PART = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(억|천만|백만|만|천)?")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*(%p|%)")  # %p 와 % 는 다른 값
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_KO_DATE = re.compile(r"(?:(\d{4})\s*년\s*)?(\d{1,2})\s*월\s*(\d{1,2})\s*일")
_COUNT = re.compile(r"(\d[\d,]*)\s*(인|건|곳|개월|년|일|점|세)")  # 자격 조건 수치
_NAME = re.compile(r"「([^」]+)」")  # 「」 밖 사업명은 9스텝 교차 검증이 본다


def _won(phrase: str) -> int:
    """'1억 400만원' → 104000000"""
    return round(sum(float(n.replace(",", "")) * _UNITS.get(u, 1) for n, u in _MONEY_PART.findall(phrase)))


def _facts(text: str) -> dict[str, set]:
    """대조할 값을 종류별로 뽑는다. 날짜를 먼저 지워야 '18일' 이 수치로 안 잡힌다."""
    no_dates = _KO_DATE.sub(" ", _ISO_DATE.sub(" ", text))
    return {
        "금액": {_won(m) for m in _MONEY.findall(no_dates)},
        "비율": {(float(n), u) for n, u in _PERCENT.findall(no_dates)},
        "날짜": {(int(y), int(m), int(d)) for y, m, d in _ISO_DATE.findall(text)}
              | {(int(y) if y else None, int(m), int(d)) for y, m, d in _KO_DATE.findall(text)},
        "수치": {(int(n.replace(",", "")), u) for n, u in _COUNT.findall(no_dates)},
        "사업명": set(_NAME.findall(text)),
    }


def check(report: str, context: str) -> list[str]:
    """리포트에만 있고 근거엔 없는 값 목록. 비면 통과."""
    got, allowed = _facts(report), _facts(context)
    bad = [f"금액 {v:,}원" for v in sorted(got["금액"] - allowed["금액"])]
    bad += [f"비율 {n:g}{u}" for n, u in sorted(got["비율"] - allowed["비율"])]

    allowed_md = {(m, d) for _, m, d in allowed["날짜"]}  # 연도 없이 쓴 날짜는 월·일만 비교
    for y, m, d in sorted(got["날짜"], key=str):
        if not ((y, m, d) in allowed["날짜"] if y else (m, d) in allowed_md):
            bad.append(f"날짜 {y}-{m:02}-{d:02}" if y else f"날짜 {m}월 {d}일")

    bad += [f"수치 {n}{u}" for n, u in sorted(got["수치"] - allowed["수치"])]
    bad += [f"사업명 「{n}」" for n in sorted(got["사업명"] - allowed["사업명"])]
    return bad
