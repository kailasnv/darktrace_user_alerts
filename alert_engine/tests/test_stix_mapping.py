from alert_engine.engine import evaluate_alerts
from alert_engine.models import EnrichedFinding
from alert_engine.stix.mapping import map_finding_to_stix_objects
from mock_data import MOCK_FINDING_CRITICAL


def test_mapping_produces_indicators_threat_actor_and_relationships(db_session):
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    alert = evaluate_alerts(finding, session=db_session)

    objects = map_finding_to_stix_objects(finding, alert)
    type_counts = {}
    for obj in objects:
        type_counts[obj.type] = type_counts.get(obj.type, 0) + 1

    assert type_counts.get("indicator", 0) == len(finding.indicators)
    assert type_counts.get("threat-actor", 0) == 1
    assert type_counts.get("observed-data", 0) == 1
    assert type_counts.get("relationship", 0) > 0


def test_indicator_pattern_uses_correct_stix_syntax(db_session):
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    alert = evaluate_alerts(finding, session=db_session)
    objects = map_finding_to_stix_objects(finding, alert)
    indicators = [o for o in objects if o.type == "indicator"]
    patterns = [i.pattern for i in indicators]
    assert any("email-addr:value" in p for p in patterns)
    assert any("file:hashes" in p for p in patterns)
