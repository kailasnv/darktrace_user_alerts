from alert_engine.db import ExportAuditRecord
from alert_engine.engine import evaluate_alerts
from alert_engine.models import EnrichedFinding
from alert_engine.stix.taxii_client import TaxiiPublishResult
from alert_engine.stix.export import export_alert_to_taxii
from mock_data import MOCK_FINDING_CRITICAL
from sqlalchemy import select


class _FakeSuccessClient:
    def publish_bundle(self, bundle_json: str) -> TaxiiPublishResult:
        return TaxiiPublishResult(success=True, status_code=202, response_body={"status": "pending"})


class _FakeFailureClient:
    def publish_bundle(self, bundle_json: str) -> TaxiiPublishResult:
        return TaxiiPublishResult(success=False, status_code=500, response_body=None, error_message="server error")


def test_successful_export_records_audit(db_session):
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    alert = evaluate_alerts(finding, session=db_session)

    result = export_alert_to_taxii(alert, finding, session=db_session, client=_FakeSuccessClient())
    db_session.commit()

    assert result.success is True

    audits = db_session.execute(select(ExportAuditRecord)).scalars().all()
    assert len(audits) == 1
    assert audits[0].status == "success"
    assert audits[0].alert_id == alert.alert_id


def test_failed_export_records_audit_with_error(db_session):
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    alert = evaluate_alerts(finding, session=db_session)

    result = export_alert_to_taxii(alert, finding, session=db_session, client=_FakeFailureClient())
    db_session.commit()

    assert result.success is False

    audits = db_session.execute(select(ExportAuditRecord)).scalars().all()
    assert audits[0].status == "failed"
    assert audits[0].error_message == "server error"


def test_retry_after_failure_creates_second_audit_entry(db_session):
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    alert = evaluate_alerts(finding, session=db_session)

    export_alert_to_taxii(alert, finding, session=db_session, client=_FakeFailureClient())
    export_alert_to_taxii(alert, finding, session=db_session, client=_FakeSuccessClient())
    db_session.commit()

    audits = db_session.execute(select(ExportAuditRecord)).scalars().all()
    assert len(audits) == 2
    assert audits[0].status == "failed"
    assert audits[1].status == "success"
