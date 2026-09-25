import json

import pytest

from alert_engine.engine import evaluate_alerts
from alert_engine.models import EnrichedFinding
from alert_engine.stix.bundle import bundle_to_json, create_bundle
from alert_engine.stix.mapping import map_finding_to_stix_objects
from mock_data import MOCK_FINDING_CRITICAL


def test_bundle_is_valid_stix_21_json(db_session):
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    alert = evaluate_alerts(finding, session=db_session)
    objects = map_finding_to_stix_objects(finding, alert)

    bundle = create_bundle(objects)
    payload = json.loads(bundle_to_json(bundle))

    assert payload["type"] == "bundle"
    assert payload["id"].startswith("bundle--")
    assert len(payload["objects"]) == len(objects)


def test_empty_objects_raises():
    with pytest.raises(ValueError):
        create_bundle([])
