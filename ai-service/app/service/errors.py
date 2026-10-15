"""서비스 계층 예외. HTTP 상태 매핑은 main.py 의 예외 핸들러가 한 곳에서 한다."""


class NotFoundError(Exception):
    """404 — 없는 자치구·행정동·업종·진단 ID."""


class GoneError(Exception):
    """410 — 만료된 진단 공유 링크(F-DIA-08 24시간)."""


class InvalidInputError(Exception):
    """422 — 형식은 맞지만 데이터와 맞지 않는 입력."""


class NotReadyError(Exception):
    """503 — 모델·인덱스가 아직 적재되지 않았다."""
