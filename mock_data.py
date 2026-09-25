from __future__ import annotations

MOCK_FINDING_LOW = {
    "finding_id": "TEST-LOW-001",
    "threat_type": "brand_impersonation",
    "confidence": 0.15,
    "source_id": "darktrace",
    "watchlist_id": "WL-001",
    "tenant_id": "tenant-demo",
    "indicators": [],
    "signals": {
        "keyword": 0.10,
        "classification": 0.30,
        "entities": 0.00,
        "history": 0.20,
        "behavior": 0.25,
        "temporal": 0.40,
        "feedback": 0.30,
    },
}

MOCK_FINDING_MEDIUM = {
    "finding_id": "TEST-MED-001",
    "threat_type": "phishing",
    "confidence": 0.55,
    "source_id": "darktrace",
    "watchlist_id": "WL-001",
    "tenant_id": "tenant-demo",
    "indicators": [
        {"type": "url", "value": "http://phish-example.test/login"},
        {"type": "email", "value": "attacker@phish-example.test"},
    ],
    "signals": {
        "keyword": 0.50,
        "classification": 0.55,
        "entities": 0.55,
        "history": 0.50,
        "behavior": 0.50,
        "temporal": 0.50,
        "feedback": 0.50,
    },
}

MOCK_FINDING_HIGH = {
    "finding_id": "TEST-HIGH-001",
    "threat_type": "unauthorized_access",
    "confidence": 0.80,
    "source_id": "darktrace",
    "watchlist_id": "WL-002",
    "tenant_id": "tenant-demo",
    "indicators": [
        {"type": "ip", "value": "203.0.113.42"},
        {"type": "credential", "value": "svc-admin@example.com"},
    ],
    "signals": {
        "keyword": 0.75,
        "classification": 0.75,
        "entities": 0.75,
        "history": 0.60,
        "behavior": 0.70,
        "temporal": 0.60,
        "feedback": 0.60,
    },
}

MOCK_FINDING_CRITICAL = {
    "finding_id": "TEST-CRIT-001",
    "threat_type": "ransomware",
    "confidence": 0.95,
    "source_id": "darktrace",
    "watchlist_id": "WL-003",
    "tenant_id": "tenant-demo",
    "indicators": [
        {"type": "email", "value": "admin@example.com"},
        {"type": "ip", "value": "198.51.100.23"},
        {
            "type": "file_hash",
            "value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
    ],
    "threat_actor": {
        "name": "Unattributed Ransomware Affiliate",
        "types": ["crime-syndicate"],
        "description": "Actor observed deploying ransomware payloads following credential exposure",
        "sophistication": "intermediate",
    },
    "signals": {
        "keyword": 0.95,
        "classification": 0.97,
        "entities": 0.90,
        "history": 0.70,
        "behavior": 0.85,
        "temporal": 0.60,
        "feedback": 0.55,
    },
}

MOCK_FINDING_DARKTRACE_RAW = {
    "finding_id": "TEST-001",
    "threat_type": "credential_exposure",
    "confidence": 0.92,
    "source_id": "darktrace",
    "indicators": [{"type": "email", "value": "admin@example.com"}],
}

MOCK_FINDING_ACTOR_COMPANY_A = {
    "finding_id": "TEST-CORR-A-001",
    "threat_type": "credential_exposure",
    "confidence": 0.70,
    "source_id": "darktrace",
    "watchlist_id": "WL-010",
    "tenant_id": "tenant-company-a",
    "indicators": [{"type": "email", "value": "breach@shared-actor.test"}],
    "threat_actor": {
        "name": "Actor X",
        "types": ["crime-syndicate"],
        "description": "Actor observed harvesting and reselling credentials across multiple targets",
    },
}

MOCK_FINDING_ACTOR_COMPANY_B = {
    "finding_id": "TEST-CORR-B-001",
    "threat_type": "credential_exposure",
    "confidence": 0.72,
    "source_id": "darktrace",
    "watchlist_id": "WL-020",
    "tenant_id": "tenant-company-b",
    "indicators": [{"type": "domain", "value": "shared-actor-infra.test"}],
    "threat_actor": {
        "name": "Actor X",
        "types": ["crime-syndicate"],
        "description": "Same actor observed targeting a second organization",
    },
}
