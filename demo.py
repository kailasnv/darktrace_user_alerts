from __future__ import annotations

import json

from alert_engine.db import init_db
from alert_engine.engine import evaluate_alerts
from alert_engine.models import EnrichedFinding
from alert_engine.stix.bundle import bundle_to_json, create_bundle
from alert_engine.stix.mapping import map_finding_to_stix_objects
from mock_data import MOCK_FINDING_CRITICAL


def main() -> None:
    init_db()
    finding = EnrichedFinding.model_validate(MOCK_FINDING_CRITICAL)
    alert = evaluate_alerts(finding)
    print(json.dumps(alert.to_channel_payload(), indent=2))

    objects = map_finding_to_stix_objects(finding, alert)
    bundle = create_bundle(objects)
    print(bundle_to_json(bundle))


if __name__ == "__main__":
    main()
