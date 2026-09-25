from __future__ import annotations
from .db import AlertRecord, record_alert_audit
from .config import LIFECYCLE_TRANSITIONS
from .models import AlertState
from sqlalchemy.orm import Session

class InvalidLifecycleTransition(Exception):
    pass


def can_transition(current: AlertState, target: AlertState) -> bool:
    allowed = LIFECYCLE_TRANSITIONS.get(current.value, [])
    return target.value in allowed


def transition(current: AlertState, target: AlertState) -> AlertState:
    if current == target:
        return current
    if not can_transition(current, target):
        raise InvalidLifecycleTransition(f"Cannot transition alert from '{current.value}' to '{target.value}'")
    return target
def transition_and_audit(
    session: Session,
    alert: AlertRecord,
    target: AlertState,
    actor_id: str = "system",
    reason: str | None = None,
) -> AlertState:
    current = AlertState(alert.state)

    new_state = transition(current, target)

    if new_state == current:
        return current

    alert.state = new_state.value

    record_alert_audit(
        session=session,
        alert_id=alert.alert_id,
        action="ALERT_STATE_CHANGED",
        actor_id=actor_id,
        from_state=current.value,
        to_state=new_state.value,
        reason=reason,
    )

    return new_state


