# [역할] 서비스 예외 — 404·410·422·503 에 대응하는 예외 클래스를 정의한다.
"""서비스 계층 예외. HTTP 상태 매핑은 main.py 의 예외 핸들러가 한 곳에서 한다."""


# 찾는 대상이 없을 때 던진다 → main.py 가 404 로 바꾼다.
class NotFoundError(Exception):
    """404 — 없는 자치구·행정동·업종·진단 ID."""


# 공유 링크 유효기간이 지났을 때 던진다 → 410 Gone.
class GoneError(Exception):
    """410 — 만료된 진단 공유 링크(F-DIA-08 24시간)."""


# 형식은 맞지만 DB 데이터와 맞지 않는 입력일 때 던진다 → 422.
class InvalidInputError(Exception):
    """422 — 형식은 맞지만 데이터와 맞지 않는 입력."""


# 모델·인덱스·데이터가 아직 준비되지 않았을 때 던진다 → 503.
class NotReadyError(Exception):
    """503 — 모델·인덱스가 아직 적재되지 않았다."""
