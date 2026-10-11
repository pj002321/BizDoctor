"""F-DIA-08 진단 결과 저장/조회. 매출 실금액은 받지도 저장하지도 않는다(F-SYS-05)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.model.tables import diagnosis


def save(
    db: Session,
    *,
    diagnosis_id: UUID,
    district_code: str,
    industry_code: str,
    sales_index: list[float],
    signal: dict,
    feature_fallback: bool,
    created_at: datetime,
    expires_at: datetime | None,
) -> None:
    db.execute(
        insert(diagnosis).values(
            diagnosis_id=diagnosis_id,
            district_code=district_code,
            industry_code=industry_code,
            sales_index=sales_index,
            signal=signal,
            feature_fallback=feature_fallback,
            created_at=created_at,
            expires_at=expires_at,
        )
    )
    db.commit()


def get(db: Session, diagnosis_id: UUID) -> dict | None:
    r = db.execute(select(diagnosis).where(diagnosis.c.diagnosis_id == diagnosis_id)).first()
    return dict(r._mapping) if r else None
