import pytest
from pydantic import ValidationError

from app.schemas.common import FilterMeta, MarketFilter
from app.schemas.diagnosis import DiagnosisRequest
from app.schemas.signal import SignalResponse

SOL = {"title": "t", "agency": "a", "summary": "s", "limit": None, "rate": None, "url": None, "source_doc_id": "D1"}
SIG = {
    "risk_level": "RED", "risk_type": "고금리_과다채무형", "risk_type_confidence": 0.61,
    "score": 32, "visual_theme": "red", "solutions": [SOL],
}


class TestSignal:
    def test_spec_example_valid(self):
        s = SignalResponse.model_validate(SIG)
        assert s.model_dump(mode="json") == SIG

    def test_fields_exactly_spec(self):
        assert set(SignalResponse.model_fields) == {
            "risk_level", "risk_type", "risk_type_confidence", "score", "visual_theme", "solutions"}
        assert set(SIG["solutions"][0]) == {"title", "agency", "summary", "limit", "rate", "url", "source_doc_id"}

    def test_debug_field_blocked(self):
        with pytest.raises(ValidationError):
            SignalResponse.model_validate({**SIG, "solutions": [{**SOL, "_similarity_score": 0.3}]})

    @pytest.mark.parametrize("patch", [{"risk_level": "YELLOW"}, {"visual_theme": "green"}, {"risk_type": "없는유형"},
                                       {"score": 101}, {"risk_type_confidence": 1.2}])
    def test_inconsistent_rejected(self, patch):
        with pytest.raises(ValidationError):
            SignalResponse.model_validate({**SIG, **patch})


class TestDiagnosisRequest:
    def test_ok(self):
        r = DiagnosisRequest(district_code="11440660", industry_code="CS100001", monthly_sales=[1, 2, 3])
        assert "monthly_sales" not in repr(r)

    @pytest.mark.parametrize("sales", [[0, 1, 1], [1, 1], [1, -1, 1]])
    def test_bad_sales(self, sales):
        with pytest.raises(ValidationError):
            DiagnosisRequest(district_code="11440660", industry_code="CS100001", monthly_sales=sales)

    def test_bad_codes(self):
        with pytest.raises(ValidationError):
            DiagnosisRequest(district_code="마포", industry_code="CS100001", monthly_sales=[1, 1, 1])


class TestFilter:
    def test_default_min_store(self):
        assert MarketFilter().min_store_count == 5

    def test_period_order(self):
        with pytest.raises(ValidationError):
            MarketFilter(start_quarter="2025Q1", end_quarter="2024Q4")

    def test_meta(self):
        f = MarketFilter(gu="마포구", start_quarter="2024Q1")
        m = FilterMeta.of(f, {"gu", "min_store_count"})
        assert m.applied_filters == ["gu", "min_store_count"] and m.ignored_filters == ["start_quarter"]
