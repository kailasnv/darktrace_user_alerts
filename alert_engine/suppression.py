from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SuppressionRuleRecord
from .models import EnrichedFinding
from .time_utils import as_utc


def _rule_matches(rule: SuppressionRuleRecord, finding: EnrichedFinding) -> bool:
    if rule.source_id and rule.source_id != finding.source_id:
        return False
    if rule.tenant_id and rule.tenant_id != finding.tenant_id:
        return False
    if rule.threat_type and rule.threat_type != finding.threat_type:
        return False
    if rule.indicator_value:
        indicator_values = {i.value.lower() for i in finding.indicators}
        if rule.indicator_value.lower() not in indicator_values:
            return False
    return True


def check_suppression(
    session: Session,
    finding: EnrichedFinding,
    now: Optional[datetime] = None,
) -> Tuple[bool, Optional[str]]:
    reference_time = now or datetime.now(timezone.utc)
    stmt = select(SuppressionRuleRecord).where(SuppressionRuleRecord.active.is_(True))
    rules = session.execute(stmt).scalars().all()
    for rule in rules:
        if rule.expires_at is not None and reference_time >= as_utc(rule.expires_at):
            continue
        if _rule_matches(rule, finding):
            return True, rule.reason
    return False, None
