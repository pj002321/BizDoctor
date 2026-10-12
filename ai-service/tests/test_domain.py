import pytest

from app.domain import quarter as qt
from app.domain.distribution import histogram
from app.domain.market_signal import (
    MarketSignalLight,
    is_small_sample,
    signal_light,
    top_percent,
)
from app.domain.risk_type import (
    RISK_TYPE_TO_LEVEL,
    RiskLevel,
    RiskType,
    VisualTheme,
    level_of,
    theme_of,
)
from app.domain.sales_index import (
    SalesInputError,
    index_to_model_sequence,
    to_sales_index,
)
from app.domain.trend import find_reversals


class TestSalesIndex:
    def test_first_month_is_100(self):
        assert to_sales_index([12_000_000, 11_000_000, 9_000_000]) == [100.0, 91.6667, 75.0]

    def test_model_sequence_is_ratio_not_percent(self):
        assert index_to_model_sequence([100.0, 90.0, 75.0]) == [[1.0], [0.9], [0.75]]

    @pytest.mark.parametrize(
        "amounts",
        [[0, 100, 100], [100, 100], [100, 100, 100, 100], [100, -1, 100], [100, float("nan"), 1], [100, float("inf"), 1]],
    )
    def test_rejects(self, amounts):
        with pytest.raises(SalesInputError):
            to_sales_index(amounts)

    def test_later_zero_month_allowed(self):
        assert to_sales_index([100, 0, 50]) == [100.0, 0.0, 50.0]

    def test_max_amount(self):
        with pytest.raises(SalesInputError):
            to_sales_index([1, 2, 10**12], max_amount=10**11)

    def test_error_message_has_no_amount(self):
        with pytest.raises(SalesInputError) as e:
            to_sales_index([5_555_555, -7_777_777, 1])
        assert "7777777" not in str(e.value) and "7,777,777" not in str(e.value)


class TestQuarter:
    def test_roundtrip(self):
        assert qt.api_to_db("2025Q4") == "20254"
        assert qt.db_to_api("20231") == "2023Q1"
        assert qt.db_to_api(20253) == "2025Q3"

    @pytest.mark.parametrize("bad", ["2025Q5", "2025-Q1", "25Q1", "20254"])
    def test_bad_api(self, bad):
        with pytest.raises(ValueError):
            qt.api_to_db(bad)


class TestMarketSignal:
    @pytest.mark.parametrize(
        "w,expected",
        [(0.0, "GREEN"), (0.60, "GREEN"), (0.6001, "YELLOW"), (0.85, "YELLOW"), (0.8501, "RED"), (None, None)],
    )
    def test_boundaries(self, w, expected):
        got = signal_light(w, green_max=0.60, yellow_max=0.85)
        assert (got.value if got else None) == expected

    def test_small_sample_includes_5(self):
        assert is_small_sample(5, threshold=5) and not is_small_sample(6, threshold=5)
        assert is_small_sample(None, threshold=5)

    def test_top_percent(self):
        assert top_percent(0.82) == 18
        assert top_percent(1.0) == 1
        assert top_percent(0.0) == 100

    def test_market_light_is_separate_type(self):
        assert MarketSignalLight is not RiskLevel


class TestRiskType:
    def test_all_six_mapped(self):
        assert set(RISK_TYPE_TO_LEVEL) == set(RiskType) and len(RiskType) == 6

    def test_theme(self):
        assert level_of("고금리_과다채무형") == RiskLevel.RED
        assert theme_of(RiskLevel.RED) == VisualTheme.red


def test_reversals():
    rows = [
        ("A", "20232", 3.0, 2.0),
        ("A", "20231", 3.0, 2.0),
        ("A", "20233", 2.0, 2.0),
        ("A", "20241", 1.5, 2.5),
        ("A", "20242", None, 2.0),
        ("A", "20243", 3.0, 2.0),
        ("B", "20231", 1.0, 2.0),
    ]
    got = [(r.group, r.quarter, r.direction) for r in find_reversals(rows)]
    assert got == [("A", "20241", "closure_over_open"), ("A", "20243", "open_over_closure")]


def test_histogram_clips_outliers():
    bins = histogram([0, 0, 10, 20, 300], bins=2, upper_clip=20)
    assert [b[2] for b in bins] == [2, 3]
    assert histogram([]) == []
    assert histogram([5, 5]) == [(5, 5, 2)]
