from alert_engine.engine import evaluate_alerts
from mock_data import MOCK_FINDING_ACTOR_COMPANY_A, MOCK_FINDING_ACTOR_COMPANY_B, MOCK_FINDING_LOW


def test_shared_actor_correlates_across_tenants(db_session):
    alert_a = evaluate_alerts(MOCK_FINDING_ACTOR_COMPANY_A, session=db_session)
    db_session.commit()

    alert_b = evaluate_alerts(MOCK_FINDING_ACTOR_COMPANY_B, session=db_session)
    db_session.commit()

    assert alert_a.tenant_id != alert_b.tenant_id
    assert alert_a.alert_id in alert_b.related_alert_ids


def test_unrelated_finding_has_no_correlation(db_session):
    evaluate_alerts(MOCK_FINDING_ACTOR_COMPANY_A, session=db_session)
    db_session.commit()

    unrelated = evaluate_alerts(MOCK_FINDING_LOW, session=db_session)
    db_session.commit()

    assert unrelated.related_alert_ids == []


def test_shared_indicator_correlates_even_without_actor(db_session):
    finding_a = dict(MOCK_FINDING_LOW)
    finding_a["finding_id"] = "TEST-SHARED-IOC-A"
    finding_a["indicators"] = [{"type": "domain", "value": "shared-infra.test"}]
    finding_a.pop("signals", None)

    finding_b = dict(finding_a)
    finding_b["finding_id"] = "TEST-SHARED-IOC-B"
    finding_b["watchlist_id"] = "WL-999"

    alert_a = evaluate_alerts(finding_a, session=db_session)
    db_session.commit()

    alert_b = evaluate_alerts(finding_b, session=db_session)
    db_session.commit()

    assert alert_a.alert_id != alert_b.alert_id
    assert alert_a.alert_id in alert_b.related_alert_ids
