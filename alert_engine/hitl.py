from __future__ import annotations

from .config import (
    STIX_TAXII_AUTO_APPROVE_SEVERITIES,
    STIX_TAXII_EXCLUDED_SEVERITIES,
    STIX_TAXII_REQUIRES_APPROVAL_SEVERITIES,
)
from .models import Alert, Severity, StixExportStatus


class HitlPolicyError(Exception):
    pass


def determine_stix_export_status(severity: Severity) -> StixExportStatus:
    value = severity.value if isinstance(severity, Severity) else str(severity)
    if value in STIX_TAXII_EXCLUDED_SEVERITIES:
        return StixExportStatus.NOT_REQUIRED
    if value in STIX_TAXII_AUTO_APPROVE_SEVERITIES:
        return StixExportStatus.APPROVED
    if value in STIX_TAXII_REQUIRES_APPROVAL_SEVERITIES:
        return StixExportStatus.PENDING_APPROVAL
    return StixExportStatus.NOT_REQUIRED


def approve_stix_export(alert: Alert) -> Alert:
    if alert.stix_export_status != StixExportStatus.PENDING_APPROVAL:
        raise HitlPolicyError(
            f"Alert {alert.alert_id} is not awaiting approval (status: {alert.stix_export_status})"
        )
    alert.stix_export_status = StixExportStatus.APPROVED
    return alert


def reject_stix_export(alert: Alert) -> Alert:
    if alert.stix_export_status != StixExportStatus.PENDING_APPROVAL:
        raise HitlPolicyError(
            f"Alert {alert.alert_id} is not awaiting approval (status: {alert.stix_export_status})"
        )
    alert.stix_export_status = StixExportStatus.REJECTED
    return alert
