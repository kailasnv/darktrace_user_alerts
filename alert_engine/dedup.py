from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import DEDUP_WINDOW_HOURS
from .db import AlertRecord


def find_active_duplicate(
    session: Session,
    fingerprint: str,
    tenant_id: Optional[str],
    window_hours: int = DEDUP_WINDOW_HOURS,
    now: Optional[datetime] = None,
) -> Optional[AlertRecord]:
    reference_time = now or datetime.now(timezone.utc)
    window_start = reference_time - timedelta(hours=window_hours)
    stmt = (
        select(AlertRecord)
        .where(AlertRecord.fingerprint == fingerprint)
        .where(AlertRecord.tenant_id == tenant_id)
        .where(AlertRecord.last_seen >= window_start)
        .where(AlertRecord.state != "closed")
        .order_by(AlertRecord.last_seen.desc())
    )
    return session.execute(stmt).scalars().first()
