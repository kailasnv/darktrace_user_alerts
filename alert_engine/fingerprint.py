from __future__ import annotations

import hashlib
from typing import Iterable

from .models import EnrichedFinding, Indicator


def _normalized_indicator_signature(indicators: Iterable[Indicator]) -> str:
    parts = sorted(f"{i.type}:{i.value.lower()}" for i in indicators)
    return "|".join(parts)


def compute_fingerprint(finding: EnrichedFinding) -> str:
    tenant = finding.tenant_id or ""
    watchlist = finding.watchlist_id or ""
    indicator_sig = _normalized_indicator_signature(finding.indicators)
    raw_key = "::".join(
        [
            tenant,
            finding.source_id,
            watchlist,
            finding.threat_type,
            indicator_sig,
        ]
    )
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return digest
