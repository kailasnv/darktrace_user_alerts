from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..config import TAXII_CONFIG
from ..db import ExportAuditRecord, get_session
from ..engine import persist_alert
from ..models import Alert, EnrichedFinding, StixExportStatus
from .bundle import bundle_to_json, create_bundle
from .mapping import map_finding_to_stix_objects
from .taxii_client import TaxiiClient, TaxiiPublishResult

logger = logging.getLogger("alert_engine.stix_export")


class StixExportError(Exception):
    pass


def alert_to_finding_projection(alert: Alert) -> EnrichedFinding:
    return EnrichedFinding(
        finding_id=alert.finding_id,
        threat_type=alert.threat_type,
        confidence=alert.confidence,
        source_id=alert.source_id,
        watchlist_id=alert.watchlist_id,
        tenant_id=alert.tenant_id,
        indicators=alert.indicators,
        threat_actor=alert.threat_actor,
        context=alert.context,
        observed_at=alert.first_seen,
    )


_EXPORTABLE_STATUSES = {StixExportStatus.APPROVED, StixExportStatus.EXPORTED, StixExportStatus.FAILED}


def export_alert_to_taxii(
    alert: Alert,
    finding: EnrichedFinding,
    session: Optional[Session] = None,
    client: Optional[TaxiiClient] = None,
) -> TaxiiPublishResult:
    if alert.stix_export_status not in _EXPORTABLE_STATUSES:
        raise StixExportError(
            f"Alert {alert.alert_id} has STIX export status "
            f"'{alert.stix_export_status.value if isinstance(alert.stix_export_status, StixExportStatus) else alert.stix_export_status}' "
            "— export requires an APPROVED status (auto-approved for critical, or analyst sign-off for medium/high); "
            "a prior FAILED or EXPORTED attempt may be retried without re-approval"
        )

    objects = map_finding_to_stix_objects(finding, alert)
    if not objects:
        raise StixExportError("No mappable STIX objects were produced from this finding")

    bundle = create_bundle(objects)
    bundle_json = bundle_to_json(bundle)

    active_client = client or TaxiiClient(TAXII_CONFIG)

    try:
        result = active_client.publish_bundle(bundle_json)
    except Exception as exc:
        result = TaxiiPublishResult(success=False, status_code=None, response_body=None, error_message=str(exc))

    owns_session = session is None
    ctx = get_session() if owns_session else _passthrough(session)
    with ctx as active_session:
        audit = ExportAuditRecord(
            alert_id=alert.alert_id,
            bundle_id=bundle.id,
            collection_id=TAXII_CONFIG.collection_id,
            status="success" if result.success else "failed",
            status_code=result.status_code,
            error_message=result.error_message,
            attempted_at=datetime.now(timezone.utc),
            object_count=len(objects),
        )
        active_session.add(audit)

        alert.stix_export_status = StixExportStatus.EXPORTED if result.success else StixExportStatus.FAILED
        try:
            persist_alert(active_session, alert)
        except ValueError:
            pass

    if result.success:
        logger.info("stix.export.success", extra={"alert_id": alert.alert_id, "bundle_id": bundle.id})
    else:
        logger.error(
            "stix.export.failed",
            extra={"alert_id": alert.alert_id, "bundle_id": bundle.id, "error": result.error_message},
        )

    return result


class _passthrough:
    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, exc_type, exc, tb) -> None:
        return None
