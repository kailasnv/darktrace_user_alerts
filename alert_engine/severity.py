from __future__ import annotations

from typing import Optional

from .config import get_severity_thresholds
from .models import Severity


def severity_from_score(score: int, tenant_id: Optional[str] = None) -> Severity:
    thresholds = get_severity_thresholds(tenant_id)
    for level_name, (low, high) in thresholds.items():
        if low <= score <= high:
            return Severity(level_name)
    return Severity.INFORMATIONAL
