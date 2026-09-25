from datetime import datetime, timedelta, timezone

from alert_engine.db import SuppressionRuleRecord
from alert_engine.engine import evaluate_alerts
from mock_data import MOCK_FINDING_MEDIUM


def test_matching_suppression_rule_suppresses_alert(db_session):
    rule = SuppressionRuleRecord(
        rule_id="rule-1",
        source_id=MOCK_FINDING_MEDIUM["source_id"],
        tenant_id=MOCK_FINDING_MEDIUM["tenant_id"],
        threat_type=MOCK_FINDING_MEDIUM["threat_type"],
        indicator_value=None,
        reason="known false positive vendor scanner",
        created_at=datetime.now(timezone.utc),
        expires_at=None,
        active=True,
    )
    db_session.add(rule)
    db_session.commit()

    alert = evaluate_alerts(MOCK_FINDING_MEDIUM, session=db_session)
    assert alert.suppressed is True
    assert alert.routing.channels == []
    assert alert.suppression_reason == "known false positive vendor scanner"


def test_expired_suppression_rule_does_not_suppress(db_session):
    rule = SuppressionRuleRecord(
        rule_id="rule-2",
        source_id=MOCK_FINDING_MEDIUM["source_id"],
        tenant_id=MOCK_FINDING_MEDIUM["tenant_id"],
        threat_type=MOCK_FINDING_MEDIUM["threat_type"],
        indicator_value=None,
        reason="expired rule",
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        active=True,
    )
    db_session.add(rule)
    db_session.commit()

    alert = evaluate_alerts(MOCK_FINDING_MEDIUM, session=db_session)
    assert alert.suppressed is False
