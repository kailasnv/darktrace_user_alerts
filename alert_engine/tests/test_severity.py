from alert_engine.severity import severity_from_score
from alert_engine.models import Severity


def test_severity_boundaries():
    assert severity_from_score(0) == Severity.INFORMATIONAL
    assert severity_from_score(24) == Severity.INFORMATIONAL
    assert severity_from_score(25) == Severity.LOW
    assert severity_from_score(44) == Severity.LOW
    assert severity_from_score(45) == Severity.MEDIUM
    assert severity_from_score(64) == Severity.MEDIUM
    assert severity_from_score(65) == Severity.HIGH
    assert severity_from_score(84) == Severity.HIGH
    assert severity_from_score(85) == Severity.CRITICAL
    assert severity_from_score(100) == Severity.CRITICAL


def test_tenant_override_thresholds(monkeypatch):
    import alert_engine.config as config_module

    monkeypatch.setitem(
        config_module.TENANT_SEVERITY_THRESHOLDS,
        "tenant-strict",
        {
            "informational": (0, 9),
            "low": (10, 29),
            "medium": (30, 49),
            "high": (50, 69),
            "critical": (70, 100),
        },
    )
    assert severity_from_score(70, tenant_id="tenant-strict") == Severity.CRITICAL
    assert severity_from_score(70, tenant_id=None) == Severity.HIGH
