from alert_engine.engine import evaluate_alerts
from alert_engine.models import EnrichedFinding, Severity, StixExportStatus
from alert_engine.stix.export import export_alert_to_taxii
from alert_engine.stix.taxii_client import TaxiiPublishResult
from mock_data import MOCK_FINDING_CRITICAL, MOCK_FINDING_HIGH


class _FakeSuccessClient:
    def publish_bundle(self, bundle_json: str) -> TaxiiPublishResult:
        return TaxiiPublishResult(success=True, status_code=202, response_body={"status": "pending"})


def test_end_to_end_critical_mock_finding_to_taxii_export(db_session):
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)

    alert = evaluate_alerts(finding, session=db_session)
    db_session.commit()

    assert alert.severity == Severity.CRITICAL
    assert alert.state.value == "new"
    assert set(alert.routing.channels) == {"dashboard", "email", "webhook", "sms_push", "siem", "on_call"}
    assert alert.stix_export_status == StixExportStatus.APPROVED

    export_result = export_alert_to_taxii(alert, finding, session=db_session, client=_FakeSuccessClient())
    db_session.commit()

    assert export_result.success is True
    assert alert.stix_export_status == StixExportStatus.EXPORTED

    payload = alert.to_channel_payload()
    assert payload["alert_id"] == alert.alert_id
    assert payload["severity"] == "critical"
    assert payload["stix_export_status"] == "exported"
    assert "channels" in payload


def test_end_to_end_high_alert_waits_for_hitl_approval(db_session):
    finding = EnrichedFinding.model_validate(MOCK_FINDING_HIGH)

    alert = evaluate_alerts(finding, session=db_session)
    db_session.commit()

    assert alert.severity == Severity.HIGH
    assert alert.stix_export_status == StixExportStatus.PENDING_APPROVAL

    from alert_engine.stix.export import StixExportError

    try:
        export_alert_to_taxii(alert, finding, session=db_session, client=_FakeSuccessClient())
        assert False, "expected export to be blocked pending HITL approval"
    except StixExportError:
        pass
