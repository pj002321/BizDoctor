# [역할] 단위 테스트 — domain 순수 함수(지수 변환·분기·신호등·유형 매핑·역전·히스토그램)를 검증한다.
# 테스트 프레임워크.
import pytest

# 분기 변환 모듈.
from app.domain import quarter as qt
# 히스토그램 함수.
from app.domain.distribution import histogram
# 상권 신호등 관련 함수·타입.
from app.domain.market_signal import (
    # 신호등 색 타입
    MarketSignalLight,
    # 표본 적음 판정
    is_small_sample,
    # 위험가중치 → 색
    signal_light,
    # 상위 N%
    top_percent,
)
# 위험 유형 관련 타입·함수.
from app.domain.risk_type import (
    # 유형 → 등급 표
    RISK_TYPE_TO_LEVEL,
    # 진단 등급
    RiskLevel,
    # 위험 유형
    RiskType,
    # 화면 테마
    VisualTheme,
    # 유형 → 등급
    level_of,
    # 등급 → 테마
    theme_of,
)
# 매출 지수 변환 관련.
from app.domain.sales_index import (
    # 입력 오류 예외
    SalesInputError,
    # 지수 → 모델 시퀀스
    index_to_model_sequence,
    # 금액 → 지수
    to_sales_index,
)
# 역전 구간 탐지.
from app.domain.trend import find_reversals


# 매출 지수 변환 테스트 묶음.
class TestSalesIndex:
    # 1개월차가 100 이 되는지.
    def test_first_month_is_100(self):
        # 1200만·1100만·900만 → 100·91.6667·75
        assert to_sales_index([12_000_000, 11_000_000, 9_000_000]) == [100.0, 91.6667, 75.0]

    # 모델 입력은 100 이 아니라 1.0 기준인지.
    def test_model_sequence_is_ratio_not_percent(self):
        # 학습은 seq_raw / seq_raw[:, [0]] → 1개월차 = 1.0. 100 을 그대로 넣으면 100배 틀어진다.
        assert index_to_model_sequence([100.0, 90.0, 75.0]) == [[1.0], [0.9], [0.75]]

    # 아래 잘못된 입력들을 각각 넣어 본다.
    @pytest.mark.parametrize(
        # 매개변수 이름
        "amounts",
        # 1개월차 0 / 2개월 / 4개월 / 음수 / NaN / 무한대
        [[0, 100, 100], [100, 100], [100, 100, 100, 100], [100, -1, 100], [100, float("nan"), 1], [100, float("inf"), 1]],
    )
    # 잘못된 입력은 거절되는지.
    def test_rejects(self, amounts):
        # SalesInputError 가 나야 통과.
        with pytest.raises(SalesInputError):
            # 변환을 시도한다.
            to_sales_index(amounts)

    # 2·3개월차가 0 인 것은 허용되는지.
    def test_later_zero_month_allowed(self):
        # 100, 0, 50 → 100, 0, 50
        assert to_sales_index([100, 0, 50]) == [100.0, 0.0, 50.0]

    # 상한을 넘으면 거절되는지.
    def test_max_amount(self):
        # 오류가 나야 통과.
        with pytest.raises(SalesInputError):
            # 1조 원 입력, 상한 1천억 원.
            to_sales_index([1, 2, 10**12], max_amount=10**11)

    # 오류 메시지에 금액이 들어가지 않는지(개인정보).
    def test_error_message_has_no_amount(self):
        # 오류를 잡아 e 에 담는다.
        with pytest.raises(SalesInputError) as e:
            # 음수 금액으로 오류를 낸다.
            to_sales_index([5_555_555, -7_777_777, 1])
        # 메시지에 금액 숫자가 없어야 한다.
        assert "7777777" not in str(e.value) and "7,777,777" not in str(e.value)


# 분기 변환 테스트 묶음.
class TestQuarter:
    # 양방향 변환이 맞는지.
    def test_roundtrip(self):
        # API → DB
        assert qt.api_to_db("2025Q4") == "20254"
        # DB 문자열 → API
        assert qt.db_to_api("20231") == "2023Q1"
        # DB 정수 → API
        assert qt.db_to_api(20253) == "2025Q3"

    # 잘못된 API 형식 4가지를 넣어 본다.
    @pytest.mark.parametrize("bad", ["2025Q5", "2025-Q1", "25Q1", "20254"])
    # 잘못된 형식은 거절되는지.
    def test_bad_api(self, bad):
        # ValueError 가 나야 통과.
        with pytest.raises(ValueError):
            # 변환을 시도한다.
            qt.api_to_db(bad)


# 상권 신호등 테스트 묶음.
class TestMarketSignal:
    # (위험가중치, 기대 색) 쌍들 — 경계값 위주.
    @pytest.mark.parametrize(
        # 매개변수 이름
        "w,expected",
        # 0.60 은 GREEN, 0.85 는 YELLOW 까지 포함, 없으면 None.
        [(0.0, "GREEN"), (0.60, "GREEN"), (0.6001, "YELLOW"), (0.85, "YELLOW"), (0.8501, "RED"), (None, None)],
    )
    # 경계값에서 색이 맞는지.
    def test_boundaries(self, w, expected):
        # 색을 계산한다.
        got = signal_light(w, green_max=0.60, yellow_max=0.85)
        # 문자열로 비교한다(None 이면 None).
        assert (got.value if got else None) == expected

    # 점포 5개는 '표본 적음'에 포함되는지.
    def test_small_sample_includes_5(self):
        # 5 는 True, 6 은 False.
        assert is_small_sample(5, threshold=5) and not is_small_sample(6, threshold=5)
        # 점포 수를 모르면 True.
        assert is_small_sample(None, threshold=5)

    # '상위 N%' 계산이 맞는지.
    def test_top_percent(self):
        # 0.82 → 상위 18%
        assert top_percent(0.82) == 18
        # 1.0 → 0% 대신 1%
        assert top_percent(1.0) == 1  # '상위 0%' 는 표기하지 않는다
        # 0.0 → 100%
        assert top_percent(0.0) == 100

    # 상권 신호등과 진단 등급이 다른 타입인지.
    def test_market_light_is_separate_type(self):
        # F-SYS-01: 상권 신호등과 진단 등급은 다른 타입이다
        assert MarketSignalLight is not RiskLevel


# 위험 유형 테스트 묶음.
class TestRiskType:
    # 6개 유형이 모두 등급 표에 있는지.
    def test_all_six_mapped(self):
        # 표의 키 = 전체 유형, 그리고 정확히 6개.
        assert set(RISK_TYPE_TO_LEVEL) == set(RiskType) and len(RiskType) == 6

    # 유형 → 등급 → 테마 변환이 맞는지.
    def test_theme(self):
        # 고금리 채무형은 RED
        assert level_of("고금리_과다채무형") == RiskLevel.RED
        # RED 는 red 테마
        assert theme_of(RiskLevel.RED) == VisualTheme.red


# 역전 구간 탐지 테스트.
def test_reversals():
    # (그룹, 분기, 개업률, 폐업률) 테스트 데이터 — 일부러 순서를 섞었다.
    rows = [
        # 개업 > 폐업
        ("A", "20232", 3.0, 2.0),
        # 개업 > 폐업(가장 이른 분기)
        ("A", "20231", 3.0, 2.0),
        # 동률
        ("A", "20233", 2.0, 2.0),   # 동률은 건너뜀
        # 폐업 > 개업 → 역전
        ("A", "20241", 1.5, 2.5),   # 역전
        # 값 없음 → 건너뜀
        ("A", "20242", None, 2.0),
        # 개업 > 폐업 → 다시 역전
        ("A", "20243", 3.0, 2.0),   # 재역전
        # 다른 그룹, 한 분기뿐이라 역전 없음
        ("B", "20231", 1.0, 2.0),
    ]
    # 결과를 (그룹, 분기, 방향) 튜플로 바꾼다.
    got = [(r.group, r.quarter, r.direction) for r in find_reversals(rows)]
    # 두 번의 역전이 정확히 잡혀야 한다.
    assert got == [("A", "20241", "closure_over_open"), ("A", "20243", "open_over_closure")]


# 히스토그램 테스트.
def test_histogram_clips_outliers():
    # 0~20 을 2구간으로, 300 은 상한 20 으로 눌러 넣는다.
    bins = histogram([0, 0, 10, 20, 300], bins=2, upper_clip=20)
    # 첫 구간 2개(0,0), 둘째 구간 3개(10,20,300).
    assert [b[2] for b in bins] == [2, 3]  # [0,10) [10,20] — 300 은 마지막 구간
    # 빈 입력은 빈 결과.
    assert histogram([]) == []
    # 값이 모두 같으면 구간 하나.
    assert histogram([5, 5]) == [(5, 5, 2)]
