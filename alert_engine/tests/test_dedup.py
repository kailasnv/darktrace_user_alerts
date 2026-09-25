from datetime import datetime, timedelta, timezone

from alert_engine.engine import evaluate_alerts
from mock_data import MOCK_FINDING_CRITICAL


def test_duplicate_finding_updates_existing_alert(db_session):
    first = evaluate_alerts(MOCK_FINDING_CRITICAL, session=db_session)
    db_session.commit()

    second = evaluate_alerts(MOCK_FINDING_CRITICAL, session=db_session)
    db_session.commit()

    assert second.alert_id == first.alert_id
    assert second.count == 2


def test_duplicate_outside_window_creates_new_alert(db_session):
    now = datetime.now(timezone.utc)
    first = evaluate_alerts(MOCK_FINDING_CRITICAL, session=db_session, now=now - timedelta(hours=48))
    db_session.commit()

    second = evaluate_alerts(MOCK_FINDING_CRITICAL, session=db_session, now=now)
    db_session.commit()

    assert second.alert_id != first.alert_id
