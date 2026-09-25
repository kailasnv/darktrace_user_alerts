from datetime import datetime, timezone
import hashlib

SEVERITY_MAP = {
    "Informational": {
        "event_severity": 1,
        "risk_score": 10,
    },
    "Low": {
        "event_severity": 2,
        "risk_score": 30,
    },
    "Medium": {
        "event_severity": 3,
        "risk_score": 50,
    },
    "High": {
        "event_severity": 4,
        "risk_score": 75,
    },
    "Critical": {
        "event_severity": 5,
        "risk_score": 100,
    },
}


def create_siem_event(
    alert_type,
    severity,
    ioc_type,
    ioc_value,
    source,
    affected_asset,
):
    severity_data = SEVERITY_MAP[severity]

    # Create deterministic fingerprint for alert deduplication.
    # The same alert characteristics always produce the same fingerprint.
    fingerprint_data = (
        f"{alert_type}|"
        f"{ioc_value}|"
        f"{source}|"
        f"{affected_asset}"
    )

    dedup_fingerprint = hashlib.sha256(
        fingerprint_data.encode("utf-8")
    ).hexdigest()
    """
    Convert a Dark Web finding into an ECS-oriented SIEM event.
    """

    if severity not in SEVERITY_MAP:
        raise ValueError(
            f"Invalid severity: {severity}. "
            f"Expected one of: {list(SEVERITY_MAP)}"
        )

    severity_data = SEVERITY_MAP[severity]

    # Base threat indicator
    indicator = {
        "type": ioc_type,
        "name": ioc_value,
    }

    # Add ECS-specific IOC fields
    if ioc_type == "email-addr":
        indicator["email"] = {
            "address": ioc_value
        }

    elif ioc_type in ("ipv4-addr", "ipv6-addr"):
        indicator["ip"] = ioc_value

    elif ioc_type == "url":
        indicator["url"] = {
            "full": ioc_value
        }

    elif ioc_type == "file":
        indicator["file"] = {
            "hash": {
                "sha256": ioc_value
            }
        }

    elif ioc_type == "domain-name":
        # ECS does not define threat.indicator.domain.name.
        # Keep the domain in the standard indicator name field.
        pass

    event = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),

        "message": f"Dark web alert: {alert_type}",

        "event": {
            "kind": "alert",
            "category": ["threat"],
            "type": ["indicator"],
            "severity": severity_data["event_severity"],
        },

        "rule": {
            "name": alert_type,
        },

        "threat": {
            "indicator": indicator,
        },

        "source": {
            "domain": source,
        },

        "labels": {
            "alert_severity": severity,
            "affected_asset": affected_asset,
            "alert_source": "dark_web_monitoring",
            "dedup_fingerprint": dedup_fingerprint,
        },

        "risk": {
            "score": severity_data["risk_score"],
        },
    }

    return event
