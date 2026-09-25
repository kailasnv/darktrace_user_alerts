from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .correlation import extract_indicator_values, extract_threat_actor_name, find_related_alert_ids
from .db import AlertRecord, get_session
from .dedup import find_active_duplicate
from .fingerprint import compute_fingerprint
from .hitl import determine_stix_export_status
from .lifecycle import transition
from .models import Alert, AlertState, EnrichedFinding, RoutingDecision, Severity, StixExportStatus
from .risk import compute_risk_breakdown, compute_risk_score
from .routing import decide_routing
from .severity import severity_from_score
from .suppression import check_suppression

logger = logging.getLogger("alert_engine")

_STIX_STATUSES_LOCKED_FROM_RECOMPUTE = {
    StixExportStatus.APPROVED,
    StixExportStatus.REJECTED,
    StixExportStatus.EXPORTED,
    StixExportStatus.FAILED,
}


def _record_to_alert(record: AlertRecord) -> Alert:
    payload = json.loads(record.payload_json)
    return Alert.model_validate(payload)


def _record_from_alert(alert: Alert) -> AlertRecord:
    return AlertRecord(
        alert_id=alert.alert_id,
        fingerprint=alert.fingerprint,
        source_id=alert.source_id,
        watchlist_id=alert.watchlist_id,
        tenant_id=alert.tenant_id,
        finding_id=alert.finding_id,
        threat_type=alert.threat_type,
        severity=alert.severity.value,
        risk_score=alert.risk_score,
        confidence=alert.confidence,
        state=alert.state.value,
        first_seen=alert.first_seen,
        last_seen=alert.last_seen,
        count=alert.count,
        suppressed=alert.suppressed,
        suppression_reason=alert.suppression_reason,
        indicator_values=json.dumps(sorted({i.value.lower() for i in alert.indicators})),
        threat_actor_name=(alert.threat_actor or {}).get("name", "").strip().lower() or None,
        stix_export_status=(
            alert.stix_export_status.value
            if isinstance(alert.stix_export_status, StixExportStatus)
            else alert.stix_export_status
        ),
        payload_json=alert.model_dump_json(),
    )


def _apply_alert_to_record(record: AlertRecord, alert: Alert) -> None:
    record.severity = alert.severity.value
    record.risk_score = alert.risk_score
    record.confidence = alert.confidence
    record.state = alert.state.value if isinstance(alert.state, AlertState) else alert.state
    record.first_seen = alert.first_seen
    record.last_seen = alert.last_seen
    record.count = alert.count
    record.suppressed = alert.suppressed
    record.suppression_reason = alert.suppression_reason
    record.indicator_values = json.dumps(sorted({i.value.lower() for i in alert.indicators}))
    record.threat_actor_name = (alert.threat_actor or {}).get("name", "").strip().lower() or None
    record.stix_export_status = (
        alert.stix_export_status.value
        if isinstance(alert.stix_export_status, StixExportStatus)
        else alert.stix_export_status
    )
    record.payload_json = alert.model_dump_json()


def _new_alert(
    finding: EnrichedFinding,
    fingerprint: str,
    risk_score: int,
    risk_breakdown: Dict[str, float],
    severity: Severity,
    now: datetime,
    suppressed: bool,
    suppression_reason: Optional[str],
    related_alert_ids: list,
) -> Alert:
    routing = RoutingDecision(channels=[]) if suppressed else decide_routing(severity)
    stix_status = StixExportStatus.NOT_REQUIRED if suppressed else determine_stix_export_status(severity)
    return Alert(
        fingerprint=fingerprint,
        source_id=finding.source_id,
        watchlist_id=finding.watchlist_id,
        tenant_id=finding.tenant_id,
        finding_id=finding.finding_id,
        threat_type=finding.threat_type,
        severity=severity,
        risk_score=risk_score,
        confidence=finding.confidence,
        state=AlertState.NEW,
        first_seen=now,
        last_seen=now,
        count=1,
        indicators=finding.indicators,
        threat_actor=finding.threat_actor,
        routing=routing,
        suppressed=suppressed,
        suppression_reason=suppression_reason,
        risk_breakdown=risk_breakdown,
        related_alert_ids=related_alert_ids,
        stix_export_status=stix_status,
        context=finding.context,
    )


def _merge_into_existing(
    existing: Alert,
    finding: EnrichedFinding,
    risk_score: int,
    risk_breakdown: Dict[str, float],
    severity: Severity,
    now: datetime,
    suppressed: bool,
    suppression_reason: Optional[str],
    related_alert_ids: list,
) -> Alert:
    existing.last_seen = now
    existing.count += 1
    existing.risk_score = max(existing.risk_score, risk_score)
    existing.risk_breakdown = risk_breakdown
    if severity != existing.severity:
        existing.severity = severity
    existing.confidence = max(existing.confidence, finding.confidence)
    existing.suppressed = suppressed
    existing.suppression_reason = suppression_reason
    if finding.threat_actor and not existing.threat_actor:
        existing.threat_actor = finding.threat_actor
    existing.related_alert_ids = related_alert_ids
    if not suppressed:
        existing.routing = decide_routing(existing.severity)
    else:
        existing.routing = RoutingDecision(channels=[])
    if existing.stix_export_status not in _STIX_STATUSES_LOCKED_FROM_RECOMPUTE:
        existing.stix_export_status = (
            StixExportStatus.NOT_REQUIRED if suppressed else determine_stix_export_status(existing.severity)
        )
    if existing.state == AlertState.CLOSED:
        existing.state = transition(existing.state, AlertState.NEW)
    return existing


def evaluate_alerts(
    enriched: Dict[str, Any] | EnrichedFinding,
    session: Optional[Session] = None,
    now: Optional[datetime] = None,
) -> Alert:
    finding = enriched if isinstance(enriched, EnrichedFinding) else EnrichedFinding.model_validate(enriched)
    reference_time = now or datetime.now(timezone.utc)

    owns_session = session is None
    ctx = get_session() if owns_session else _passthrough(session)

    with ctx as active_session:
        risk_breakdown = compute_risk_breakdown(finding)
        risk_score = compute_risk_score(finding)
        severity = severity_from_score(risk_score, tenant_id=finding.tenant_id)
        fingerprint = compute_fingerprint(finding)
        suppressed, suppression_reason = check_suppression(active_session, finding, now=reference_time)

        existing_record = find_active_duplicate(
            active_session, fingerprint, finding.tenant_id, now=reference_time
        )

        exclude_id = existing_record.alert_id if existing_record is not None else None
        related_alert_ids = find_related_alert_ids(active_session, finding, exclude_alert_id=exclude_id)

        if existing_record is not None:
            existing_alert = _record_to_alert(existing_record)
            merged = _merge_into_existing(
                existing_alert,
                finding,
                risk_score,
                risk_breakdown,
                severity,
                reference_time,
                suppressed,
                suppression_reason,
                related_alert_ids,
            )
            _apply_alert_to_record(existing_record, merged)
            logger.info("alert.updated", extra={"alert_id": merged.alert_id, "count": merged.count})
            return merged

        new_alert = _new_alert(
            finding,
            fingerprint,
            risk_score,
            risk_breakdown,
            severity,
            reference_time,
            suppressed,
            suppression_reason,
            related_alert_ids,
        )
        record = _record_from_alert(new_alert)
        active_session.add(record)
        logger.info("alert.created", extra={"alert_id": new_alert.alert_id, "severity": new_alert.severity.value})
        return new_alert


def get_alert_by_id(session: Session, alert_id: str) -> Optional[Alert]:
    record = session.get(AlertRecord, alert_id)
    if record is None:
        return None
    return _record_to_alert(record)


def persist_alert(session: Session, alert: Alert) -> None:
    record = session.get(AlertRecord, alert.alert_id)
    if record is None:
        raise ValueError(f"No stored alert with id {alert.alert_id}")
    _apply_alert_to_record(record, alert)


class _passthrough:
    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, exc_type, exc, tb) -> None:
        return None
