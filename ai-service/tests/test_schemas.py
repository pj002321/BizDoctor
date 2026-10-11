# [역할] 스키마 테스트 — 신호 JSON 계약, 진단 입력 검증, 공통 필터 동작을 검증한다.
# 테스트 프레임워크.
import pytest
# Pydantic 검증 실패 예외.
from pydantic import ValidationError

# 공통 필터와 메타.
from app.schemas.common import FilterMeta, MarketFilter
# 진단 요청 스키마.
from app.schemas.diagnosis import DiagnosisRequest
# 신호 JSON 스키마.
from app.schemas.signal import SignalResponse

# 정책자금 한 건 예시 데이터.
SOL = {"title": "t", "agency": "a", "summary": "s", "limit": None, "rate": None, "url": None, "source_doc_id": "D1"}
# 스펙 예시와 같은 형태의 신호 JSON.
SIG = {
    # 등급·유형·확률
    "risk_level": "RED", "risk_type": "고금리_과다채무형", "risk_type_confidence": 0.61,
    # 점수·테마·정책자금
    "score": 32, "visual_theme": "red", "solutions": [SOL],
}


# 신호 JSON 계약 테스트 묶음.
class TestSignal:
    # 스펙 예시가 그대로 통과하고 그대로 직렬화되는지.
    def test_spec_example_valid(self):
        # 딕셔너리를 스키마로 읽는다.
        s = SignalResponse.model_validate(SIG)
        # 다시 JSON 으로 바꿨을 때 원본과 같아야 한다.
        assert s.model_dump(mode="json") == SIG

    # 필드 목록이 스펙과 정확히 같은지.
    def test_fields_exactly_spec(self):
        # 최상위 필드 6개
        assert set(SignalResponse.model_fields) == {
            # 스펙의 필드 이름들
            "risk_level", "risk_type", "risk_type_confidence", "score", "visual_theme", "solutions"}
        # solutions[] 항목 필드 7개
        assert set(SIG["solutions"][0]) == {"title", "agency", "summary", "limit", "rate", "url", "source_doc_id"}

    # 디버그 필드가 섞이면 막히는지.
    def test_debug_field_blocked(self):
        # 검증 오류가 나야 통과.
        with pytest.raises(ValidationError):
            # _similarity_score 를 넣어 본다.
            SignalResponse.model_validate({**SIG, "solutions": [{**SOL, "_similarity_score": 0.3}]})

    # 서로 안 맞는 값·범위 밖 값을 하나씩 넣어 본다.
    @pytest.mark.parametrize("patch", [{"risk_level": "YELLOW"}, {"visual_theme": "green"}, {"risk_type": "없는유형"},
                                       # 점수 초과, 확률 초과
                                       {"score": 101}, {"risk_type_confidence": 1.2}])
    # 모두 거절되는지.
    def test_inconsistent_rejected(self, patch):
        # 검증 오류가 나야 통과.
        with pytest.raises(ValidationError):
            # 원본에 잘못된 값을 덮어써서 검증한다.
            SignalResponse.model_validate({**SIG, **patch})


# 진단 요청 검증 테스트 묶음.
class TestDiagnosisRequest:
    # 정상 입력이 통과하고 금액이 출력에 안 보이는지.
    def test_ok(self):
        # 정상 요청을 만든다.
        r = DiagnosisRequest(district_code="11440660", industry_code="CS100001", monthly_sales=[1, 2, 3])
        # repr 에 매출 필드가 없어야 한다.
        assert "monthly_sales" not in repr(r)  # 실금액이 로그로 새지 않게

    # 잘못된 매출 3가지(1개월차 0, 2개월, 음수).
    @pytest.mark.parametrize("sales", [[0, 1, 1], [1, 1], [1, -1, 1]])
    # 모두 거절되는지.
    def test_bad_sales(self, sales):
        # 검증 오류가 나야 통과.
        with pytest.raises(ValidationError):
            # 잘못된 매출로 요청을 만든다.
            DiagnosisRequest(district_code="11440660", industry_code="CS100001", monthly_sales=sales)

    # 코드 형식이 틀리면 거절되는지.
    def test_bad_codes(self):
        # 검증 오류가 나야 통과.
        with pytest.raises(ValidationError):
            # 행정동 코드에 한글을 넣는다.
            DiagnosisRequest(district_code="마포", industry_code="CS100001", monthly_sales=[1, 1, 1])


# 공통 필터 테스트 묶음.
class TestFilter:
    # 최소 점포수 기본값이 5 인지.
    def test_default_min_store(self):
        # 아무것도 안 넣고 만들면 5.
        assert MarketFilter().min_store_count == 5

    # 시작 분기가 끝 분기보다 늦으면 거절되는지.
    def test_period_order(self):
        # 검증 오류가 나야 통과.
        with pytest.raises(ValidationError):
            # 2025Q1 ~ 2024Q4
            MarketFilter(start_quarter="2025Q1", end_quarter="2024Q4")

    # 적용/무시 필터가 올바로 나뉘는지.
    def test_meta(self):
        # 자치구와 기간을 건 필터.
        f = MarketFilter(gu="마포구", start_quarter="2024Q1")
        # 이 엔드포인트는 gu·min_store_count 만 지원한다고 가정.
        m = FilterMeta.of(f, {"gu", "min_store_count"})
        # 기간은 무시 목록으로 가야 한다.
        assert m.applied_filters == ["gu", "min_store_count"] and m.ignored_filters == ["start_quarter"]
