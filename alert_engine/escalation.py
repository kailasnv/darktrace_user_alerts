from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import ESCALATION_POLICY
from .db import AlertRecord, EscalationLogRecord
from .time_utils import as_utc
from .lifecycle import transition_and_audit
from .models import AlertState




def _escalation_count(session: Session, alert_id: str) -> int:
    stmt = select(EscalationLogRecord).where(EscalationLogRecord.alert_id == alert_id)
    return len(session.execute(stmt).scalars().all())


def _last_escalation(session: Session, alert_id: str) -> Optional[EscalationLogRecord]:
    stmt = (
        select(EscalationLogRecord)
        .where(EscalationLogRecord.alert_id == alert_id)
        .order_by(EscalationLogRecord.escalated_at.desc())
    )
    return session.execute(stmt).scalars().first()


def evaluate_escalation(
    session: Session,
    alert: AlertRecord,
    now: Optional[datetime] = None,
) -> bool:
    reference_time = now or datetime.now(timezone.utc)
    policy = ESCALATION_POLICY.get(alert.severity)
    if policy is None:
        return False
    if alert.state not in {"new", "escalated"}:
        return False

    existing_count = _escalation_count(session, alert.alert_id)
    if existing_count >= policy["max_escalations"]:
        return False

    last = _last_escalation(session, alert.alert_id)
    if last is None:
        due_at = as_utc(alert.first_seen) + timedelta(minutes=policy["first_escalation_minutes"])
    else:
        due_at = as_utc(last.escalated_at) + timedelta(minutes=policy["repeat_escalation_minutes"])

    if reference_time < due_at:
        return False

    level = existing_count + 1
    reason = f"Unacknowledged {alert.severity} alert exceeded escalation interval (level {level})"
    log_entry = EscalationLogRecord(
        alert_id=alert.alert_id,
        escalated_at=reference_time,
        level=level,
        reason=reason,
    )
    session.add(log_entry)
    transition_and_audit(
        session=session,
        alert=alert,
        target=AlertState.ESCALATED,
        actor_id="system:escalation",
        reason=reason,
    )




    return True


def scan_and_escalate(session: Session, now: Optional[datetime] = None) -> List[str]:
    reference_time = now or datetime.now(timezone.utc)
    stmt = select(AlertRecord).where(AlertRecord.state.in_(["new", "escalated"]))
    candidates = session.execute(stmt).scalars().all()
    escalated_ids: List[str] = []
    for alert in candidates:
        if evaluate_escalation(session, alert, now=reference_time):
            escalated_ids.append(alert.alert_id)
    return escalated_ids
