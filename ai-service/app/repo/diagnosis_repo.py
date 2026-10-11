# [역할] 진단 저장소 — 진단 결과(지수·신호 JSON)를 저장하고 ID로 조회한다. 매출 실금액은 다루지 않는다 (F-DIA-08).
"""F-DIA-08 진단 결과 저장/조회. 매출 실금액은 받지도 저장하지도 않는다(F-SYS-05)."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 생성·만료 시각 타입.
from datetime import datetime
# 진단 ID 타입.
from uuid import UUID

# INSERT·SELECT 문을 만드는 함수.
from sqlalchemy import insert, select
# DB 세션 타입.
from sqlalchemy.orm import Session

# 진단 결과 테이블 정의.
from app.model.tables import diagnosis


# 진단 결과 한 건을 저장한다. * 뒤 인자는 이름을 붙여서만 넘길 수 있다(순서 실수 방지).
def save(
    # 요청에서 받은 DB 세션
    db: Session,
    # 이후 인자는 키워드 전용
    *,
    # 새로 만든 진단 ID
    diagnosis_id: UUID,
    # 행정동 코드
    district_code: str,
    # 업종 코드
    industry_code: str,
    # 1개월차=100 매출 지수(실금액 아님)
    sales_index: list[float],
    # 프론트로 나간 신호 JSON
    signal: dict,
    # 정적 피처 폴백이 쓰였는지
    feature_fallback: bool,
    # 생성 시각
    created_at: datetime,
    # 만료 시각(없으면 영구)
    expires_at: datetime | None,
) -> None:
    # INSERT 문을 실행한다.
    db.execute(
        # diagnosis 테이블에 아래 값들로 한 행을 넣는다.
        insert(diagnosis).values(
            # 진단 ID
            diagnosis_id=diagnosis_id,
            # 행정동 코드
            district_code=district_code,
            # 업종 코드
            industry_code=industry_code,
            # 매출 지수(JSONB)
            sales_index=sales_index,
            # 신호 JSON(JSONB)
            signal=signal,
            # 폴백 여부
            feature_fallback=feature_fallback,
            # 생성 시각
            created_at=created_at,
            # 만료 시각
            expires_at=expires_at,
        )
    )
    # 트랜잭션을 확정해 실제로 저장한다.
    db.commit()


# 진단 ID 로 한 건을 찾아 딕셔너리로 돌려준다(없으면 None).
def get(db: Session, diagnosis_id: UUID) -> dict | None:
    # ID 가 일치하는 행을 조회해 첫 행을 가져온다.
    r = db.execute(select(diagnosis).where(diagnosis.c.diagnosis_id == diagnosis_id)).first()
    # 행이 있으면 컬럼명→값 딕셔너리로, 없으면 None.
    return dict(r._mapping) if r else None
