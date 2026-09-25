from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


THREAT_TYPE_WEIGHTS: Dict[str, float] = {
    "credential_exposure": 0.85,
    "malware": 0.90,
    "phishing": 0.70,
    "data_exfiltration": 0.95,
    "ransomware": 1.00,
    "insider_threat": 0.80,
    "vulnerability_exploit": 0.75,
    "brand_impersonation": 0.50,
    "unauthorized_access": 0.80,
    "dark_web_mention": 0.60,
    "default": 0.55,
}

INDICATOR_TYPE_WEIGHTS: Dict[str, float] = {
    "email": 0.6,
    "domain": 0.7,
    "ip": 0.7,
    "url": 0.75,
    "file_hash": 0.85,
    "credential": 0.9,
    "cve": 0.9,
    "default": 0.5,
}

RISK_SIGNAL_WEIGHTS: Dict[str, float] = {
    "keyword": 0.22,
    "classification": 0.24,
    "entities": 0.10,
    "history": 0.10,
    "source_reputation": 0.10,
    "behavior": 0.08,
    "temporal": 0.04,
    "feedback": 0.08,
    "confidence": 0.04,
}

RISK_SIGNAL_NEUTRAL_DEFAULT: float = 0.5

SOURCE_REPUTATION_SCORES: Dict[str, float] = {
    "darktrace": 0.95,
    "internal_siem": 0.90,
    "default": 0.70,
}

DEFAULT_SEVERITY_THRESHOLDS: Dict[str, tuple] = {
    "informational": (0, 24),
    "low": (25, 44),
    "medium": (45, 64),
    "high": (65, 84),
    "critical": (85, 100),
}

TENANT_SEVERITY_THRESHOLDS: Dict[str, Dict[str, tuple]] = {}

DEDUP_WINDOW_HOURS: int = _env_int("ALERT_DEDUP_WINDOW_HOURS", 24)

ROUTING_POLICY: Dict[str, List[str]] = {
    "informational": ["batch_digest"],
    "low": ["batch_digest", "dashboard"],
    "medium": ["dashboard", "email"],
    "high": ["dashboard", "email", "webhook"],
    "critical": ["dashboard", "email", "webhook", "sms_push", "siem", "on_call"],
}

STIX_TAXII_AUTO_APPROVE_SEVERITIES: List[str] = ["critical"]
STIX_TAXII_REQUIRES_APPROVAL_SEVERITIES: List[str] = ["medium", "high"]
STIX_TAXII_EXCLUDED_SEVERITIES: List[str] = ["informational", "low"]

ESCALATION_POLICY: Dict[str, Dict[str, int]] = {
    "critical": {"first_escalation_minutes": 15, "repeat_escalation_minutes": 30, "max_escalations": 5},
    "high": {"first_escalation_minutes": 60, "repeat_escalation_minutes": 120, "max_escalations": 3},
}

VALID_LIFECYCLE_STATES: List[str] = [
    "new",
    "acknowledged",
    "investigating",
    "escalated",
    "dismissed",
    "closed",
]

LIFECYCLE_TRANSITIONS: Dict[str, List[str]] = {
    "new": ["acknowledged", "investigating", "escalated", "dismissed", "closed"],
    "acknowledged": ["investigating", "escalated", "dismissed", "closed"],
    "investigating": ["escalated", "dismissed", "closed"],
    "escalated": ["investigating", "dismissed", "closed"],
    "dismissed": ["closed"],
    "closed": [],
}

LIFECYCLE_STATE_ALIASES: Dict[str, str] = {
    "dismissed": "false_positive",
    "closed": "resolved",
}


@dataclass(frozen=True)
class DatabaseConfig:
    url: str = field(default_factory=lambda: _env_str("ALERT_ENGINE_DB_URL", "sqlite:///./alert_engine.db"))
    echo: bool = field(default_factory=lambda: _env_bool("ALERT_ENGINE_DB_ECHO", False))


@dataclass(frozen=True)
class TaxiiConfig:
    discovery_url: str = field(default_factory=lambda: _env_str("TAXII_DISCOVERY_URL", ""))
    api_root: str = field(default_factory=lambda: _env_str("TAXII_API_ROOT", ""))
    collection_id: str = field(default_factory=lambda: _env_str("TAXII_COLLECTION_ID", ""))
    username: str = field(default_factory=lambda: _env_str("TAXII_USERNAME", ""))
    password: str = field(default_factory=lambda: _env_str("TAXII_PASSWORD", ""))
    verify_tls: bool = field(default_factory=lambda: _env_bool("TAXII_VERIFY_TLS", True))
    timeout_seconds: int = field(default_factory=lambda: _env_int("TAXII_TIMEOUT_SECONDS", 15))
    max_retries: int = field(default_factory=lambda: _env_int("TAXII_MAX_RETRIES", 3))


@dataclass(frozen=True)
class CeleryConfig:
    broker_url: str = field(default_factory=lambda: _env_str("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    result_backend: str = field(default_factory=lambda: _env_str("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"))


DB_CONFIG = DatabaseConfig()
TAXII_CONFIG = TaxiiConfig()
CELERY_CONFIG = CeleryConfig()


def get_severity_thresholds(tenant_id: str | None) -> Dict[str, tuple]:
    if tenant_id and tenant_id in TENANT_SEVERITY_THRESHOLDS:
        return TENANT_SEVERITY_THRESHOLDS[tenant_id]
    return DEFAULT_SEVERITY_THRESHOLDS
