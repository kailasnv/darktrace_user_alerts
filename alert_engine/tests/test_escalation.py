from datetime import datetime, timedelta, timezone

from alert_engine.db import AlertRecord
from alert_engine.escalation import evaluate_escalation, scan_and_escalate


def _make_alert_record(alert_id: str, severity: str, first_seen: datetime) -> AlertRecord:
    return AlertRecord(
        alert_id=alert_id,
        fingerprint=f"fp-{alert_id}",
        source_id="darktrace",
        watchlist_id="WL-1",
        tenant_id="tenant-demo",
        finding_id=f"finding-{alert_id}",
        threat_type="ransomware",
        severity=severity,
        risk_score=95,
        confidence=0.95,
        state="new",
        first_seen=first_seen,
        last_seen=first_seen,
        count=1,
        suppressed=False,
        suppression_reason=None,
        payload_json="{}",
    )


def test_critical_alert_escalates_after_interval(db_session):
    now = datetime.now(timezone.utc)
    record = _make_alert_record("alert-1", "critical", now - timedelta(minutes=20))
    db_session.add(record)
    db_session.commit()

    escalated = evaluate_escalation(db_session, record, now=now)
    assert escalated is True
    assert record.state == "escalated"


def test_critical_alert_does_not_escalate_before_interval(db_session):
    now = datetime.now(timezone.utc)
    record = _make_alert_record("alert-2", "critical", now - timedelta(minutes=5))
    db_session.add(record)
    db_session.commit()

    escalated = evaluate_escalation(db_session, record, now=now)
    assert escalated is False
    assert record.state == "new"


def test_scan_and_escalate_returns_all_due_alerts(db_session):
    now = datetime.now(timezone.utc)
    due = _make_alert_record("alert-3", "critical", now - timedelta(minutes=30))
    not_due = _make_alert_record("alert-4", "critical", now - timedelta(minutes=1))
    db_session.add_all([due, not_due])
    db_session.commit()

    escalated_ids = scan_and_escalate(db_session, now=now)
    assert "alert-3" in escalated_ids
    assert "alert-4" not in escalated_ids
