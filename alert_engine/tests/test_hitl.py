import pytest

from alert_engine.hitl import HitlPolicyError, approve_stix_export, reject_stix_export, determine_stix_export_status
from alert_engine.models import Severity, StixExportStatus
from alert_engine.engine import evaluate_alerts
from mock_data import MOCK_FINDING_CRITICAL, MOCK_FINDING_HIGH, MOCK_FINDING_LOW, MOCK_FINDING_MEDIUM


def test_low_and_informational_do_not_require_export():
    assert determine_stix_export_status(Severity.INFORMATIONAL) == StixExportStatus.NOT_REQUIRED
    assert determine_stix_export_status(Severity.LOW) == StixExportStatus.NOT_REQUIRED


def test_medium_and_high_require_analyst_approval():
    assert determine_stix_export_status(Severity.MEDIUM) == StixExportStatus.PENDING_APPROVAL
    assert determine_stix_export_status(Severity.HIGH) == StixExportStatus.PENDING_APPROVAL


def test_critical_is_auto_approved():
    assert determine_stix_export_status(Severity.CRITICAL) == StixExportStatus.APPROVED


def test_critical_alert_from_engine_is_auto_approved(db_session):
    alert = evaluate_alerts(MOCK_FINDING_CRITICAL, session=db_session)
    assert alert.stix_export_status == StixExportStatus.APPROVED


def test_high_alert_from_engine_is_pending_approval(db_session):
    alert = evaluate_alerts(MOCK_FINDING_HIGH, session=db_session)
    assert alert.stix_export_status == StixExportStatus.PENDING_APPROVAL


def test_low_alert_from_engine_is_not_required(db_session):
    alert = evaluate_alerts(MOCK_FINDING_LOW, session=db_session)
    assert alert.stix_export_status == StixExportStatus.NOT_REQUIRED


def test_approve_pending_alert_transitions_to_approved(db_session):
    alert = evaluate_alerts(MOCK_FINDING_MEDIUM, session=db_session)
    assert alert.stix_export_status == StixExportStatus.PENDING_APPROVAL
    approve_stix_export(alert)
    assert alert.stix_export_status == StixExportStatus.APPROVED


def test_reject_pending_alert_transitions_to_rejected(db_session):
    alert = evaluate_alerts(MOCK_FINDING_MEDIUM, session=db_session)
    reject_stix_export(alert)
    assert alert.stix_export_status == StixExportStatus.REJECTED


def test_cannot_approve_alert_not_pending(db_session):
    alert = evaluate_alerts(MOCK_FINDING_CRITICAL, session=db_session)
    with pytest.raises(HitlPolicyError):
        approve_stix_export(alert)


def test_cannot_reject_alert_not_pending(db_session):
    alert = evaluate_alerts(MOCK_FINDING_LOW, session=db_session)
    with pytest.raises(HitlPolicyError):
        reject_stix_export(alert)
