from __future__ import annotations

import json
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import AlertRecord
from .models import EnrichedFinding

_CORRELATION_SCAN_LIMIT = 500
_MAX_RELATED_ALERTS = 25


def extract_indicator_values(finding: EnrichedFinding) -> List[str]:
    return sorted({i.value.lower() for i in finding.indicators})


def extract_threat_actor_name(finding: EnrichedFinding) -> Optional[str]:
    if not finding.threat_actor:
        return None
    name = finding.threat_actor.get("name")
    if not name:
        return None
    return str(name).strip().lower()


def find_related_alert_ids(
    session: Session,
    finding: EnrichedFinding,
    exclude_alert_id: Optional[str] = None,
) -> List[str]:
    indicator_values = set(extract_indicator_values(finding))
    actor_name = extract_threat_actor_name(finding)

    related: List[str] = []

    if actor_name:
        stmt = select(AlertRecord.alert_id).where(AlertRecord.threat_actor_name == actor_name)
        if exclude_alert_id:
            stmt = stmt.where(AlertRecord.alert_id != exclude_alert_id)
        related.extend(session.execute(stmt).scalars().all())

    if indicator_values:
        stmt = select(AlertRecord.alert_id, AlertRecord.indicator_values).limit(_CORRELATION_SCAN_LIMIT)
        if exclude_alert_id:
            stmt = stmt.where(AlertRecord.alert_id != exclude_alert_id)
        for alert_id, raw_values in session.execute(stmt).all():
            try:
                candidate_values = set(json.loads(raw_values or "[]"))
            except (TypeError, ValueError):
                continue
            if candidate_values & indicator_values:
                related.append(alert_id)

    deduped = list(dict.fromkeys(related))
    return deduped[:_MAX_RELATED_ALERTS]
