import logging
import os
from datetime import datetime, timezone

from sms_sender import send_sms
from push_sender import send_push

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _minimum_severity() -> str:
    return os.getenv("ALERT_MIN_SEVERITY", "low").lower()


def should_notify(severity: str) -> bool:
    minimum = _minimum_severity()

    if minimum not in SEVERITY_ORDER:
        minimum = "low"

    return SEVERITY_ORDER.get(severity.lower(), 0) >= SEVERITY_ORDER[minimum]


def build_message(alert: dict) -> str:
    severity = alert.get("severity", "unknown").upper()

    return (
        f"[DarkTrace {severity}] "
        f"{alert.get('summary', 'Threat intelligence alert')} "
        f"| Source: {alert.get('source', 'unknown')} "
        f"| Confidence: {float(alert.get('confidence', 0)):.0%} "
        f"| Alert ID: {alert.get('alert_id', 'unknown')}"
    )


def send_notifications(alert: dict) -> dict:
    severity = str(alert.get("severity", "low")).lower()

    if not should_notify(severity):
        return {
            "status": "skipped",
            "reason": f"severity below ALERT_MIN_SEVERITY ({_minimum_severity()})",
            "alert_id": alert.get("alert_id"),
        }

    channel = str(alert.get("channel", "both")).lower()
    message = build_message(alert)

    results = {
        "alert_id": alert.get("alert_id"),
        "severity": severity,
        "channel": channel,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sms": None,
        "push": None,
    }

    if channel in ("sms", "both"):
        try:
            results["sms"] = {
                "status": "success",
                "result": send_sms(
                    message,
                    alert.get("phone_number"),
                ),
            }
        except Exception as exc:
            logger.exception("SMS notification failed")
            results["sms"] = {
                "status": "failed",
                "error": str(exc),
            }

    if channel in ("push", "both"):
        try:
            results["push"] = {
                "status": "success",
                "result": send_push(
                    title=f"DarkTrace {severity.upper()} Alert",
                    body=message,
                    fcm_token=alert.get("fcm_token"),
                ),
            }
        except Exception as exc:
            logger.exception("Push notification failed")
            results["push"] = {
                "status": "failed",
                "error": str(exc),
            }

    return results
