from alert_engine.fingerprint import compute_fingerprint
from alert_engine.models import EnrichedFinding
from mock_data import MOCK_FINDING_CRITICAL


def test_fingerprint_is_stable():
    finding_a = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    finding_b = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    assert compute_fingerprint(finding_a) == compute_fingerprint(finding_b)


def test_fingerprint_differs_on_indicators():
    base = dict(MOCK_FINDING_CRITICAL)
    variant = dict(base)
    variant["indicators"] = [{"type": "email", "value": "someone-else@example.com"}]
    finding_a = EnrichedFinding.model_validate(base)
    finding_b = EnrichedFinding.model_validate(variant)
    assert compute_fingerprint(finding_a) != compute_fingerprint(finding_b)


def test_fingerprint_ignores_indicator_order():
    base = dict(MOCK_FINDING_CRITICAL)
    reordered = dict(base)
    reordered["indicators"] = list(reversed(base["indicators"]))
    finding_a = EnrichedFinding.model_validate(base)
    finding_b = EnrichedFinding.model_validate(reordered)
    assert compute_fingerprint(finding_a) == compute_fingerprint(finding_b)
