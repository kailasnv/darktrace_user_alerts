from alert_engine.config import RISK_SIGNAL_WEIGHTS
from alert_engine.models import EnrichedFinding, Severity
from alert_engine.risk import compute_risk_breakdown, compute_risk_score, resolve_signals
from alert_engine.severity import severity_from_score
from mock_data import (
    MOCK_FINDING_CRITICAL,
    MOCK_FINDING_HIGH,
    MOCK_FINDING_LOW,
    MOCK_FINDING_MEDIUM,
)


def test_weights_sum_to_one():
    assert round(sum(RISK_SIGNAL_WEIGHTS.values()), 6) == 1.0


def test_nine_signal_families_are_present():
    expected = {
        "keyword",
        "classification",
        "entities",
        "history",
        "source_reputation",
        "behavior",
        "temporal",
        "feedback",
        "confidence",
    }
    assert set(RISK_SIGNAL_WEIGHTS.keys()) == expected


def test_low_risk_finding_scores_low():
    finding = EnrichedFinding.model_validate(MOCK_FINDING_LOW)
    score = compute_risk_score(finding)
    assert severity_from_score(score) == Severity.LOW


def test_medium_risk_finding_scores_medium():
    finding = EnrichedFinding.model_validate(MOCK_FINDING_MEDIUM)
    score = compute_risk_score(finding)
    assert severity_from_score(score) == Severity.MEDIUM


def test_high_risk_finding_scores_high():
    finding = EnrichedFinding.model_validate(MOCK_FINDING_HIGH)
    score = compute_risk_score(finding)
    assert severity_from_score(score) == Severity.HIGH


def test_critical_risk_finding_scores_critical():
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    score = compute_risk_score(finding)
    assert severity_from_score(score) == Severity.CRITICAL


def test_score_is_bounded():
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    score = compute_risk_score(finding)
    assert 0 <= score <= 100


def test_explicit_signal_overrides_upstream_fallback():
    payload = dict(MOCK_FINDING_LOW)
    payload["signals"] = dict(payload["signals"], keyword=0.99)
    finding = EnrichedFinding.model_validate(payload)
    resolved = resolve_signals(finding)
    assert resolved["keyword"] == 0.99


def test_missing_signals_fall_back_to_neutral_default():
    finding = EnrichedFinding.model_validate(MOCK_FINDING_DARKTRACE_MINIMAL)
    resolved = resolve_signals(finding)
    assert resolved["keyword"] == 0.5
    assert resolved["history"] == 0.5
    assert resolved["behavior"] == 0.5
    assert resolved["feedback"] == 0.5


def test_breakdown_contributions_sum_to_score():
    finding = EnrichedFinding.model_validate(MOCK_FINDING_HIGH)
    breakdown = compute_risk_breakdown(finding)
    score = compute_risk_score(finding)
    assert round(sum(breakdown.values()) * 100) == score


MOCK_FINDING_DARKTRACE_MINIMAL = {
    "finding_id": "TEST-MINIMAL-001",
    "threat_type": "phishing",
    "confidence": 0.5,
    "source_id": "darktrace",
    "indicators": [],
}
