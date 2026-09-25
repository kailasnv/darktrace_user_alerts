from __future__ import annotations

from typing import Dict

from .config import (
    INDICATOR_TYPE_WEIGHTS,
    RISK_SIGNAL_NEUTRAL_DEFAULT,
    RISK_SIGNAL_WEIGHTS,
    SOURCE_REPUTATION_SCORES,
    THREAT_TYPE_WEIGHTS,
)
from .models import EnrichedFinding


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _classification_fallback(finding: EnrichedFinding) -> float:
    return THREAT_TYPE_WEIGHTS.get(finding.threat_type, THREAT_TYPE_WEIGHTS["default"])


def _entities_fallback(finding: EnrichedFinding) -> float:
    if not finding.indicators:
        return 0.0
    severity = max(
        INDICATOR_TYPE_WEIGHTS.get(i.type, INDICATOR_TYPE_WEIGHTS["default"]) for i in finding.indicators
    )
    volume = min(len(finding.indicators) / 3.0, 1.0)
    return _clamp((severity * 0.7) + (volume * 0.3))


def _source_reputation_fallback(finding: EnrichedFinding) -> float:
    key = finding.source_id.strip().lower()
    return SOURCE_REPUTATION_SCORES.get(key, SOURCE_REPUTATION_SCORES["default"])


def _temporal_fallback(finding: EnrichedFinding) -> float:
    hour = finding.observed_at.hour
    is_off_hours = hour < 6 or hour >= 20
    return 0.65 if is_off_hours else 0.40


def resolve_signals(finding: EnrichedFinding) -> Dict[str, float]:
    provided = finding.signals
    resolved = {
        "keyword": provided.keyword if provided.keyword is not None else RISK_SIGNAL_NEUTRAL_DEFAULT,
        "classification": (
            provided.classification if provided.classification is not None else _classification_fallback(finding)
        ),
        "entities": provided.entities if provided.entities is not None else _entities_fallback(finding),
        "history": provided.history if provided.history is not None else RISK_SIGNAL_NEUTRAL_DEFAULT,
        "source_reputation": (
            provided.source_reputation
            if provided.source_reputation is not None
            else _source_reputation_fallback(finding)
        ),
        "behavior": provided.behavior if provided.behavior is not None else RISK_SIGNAL_NEUTRAL_DEFAULT,
        "temporal": provided.temporal if provided.temporal is not None else _temporal_fallback(finding),
        "feedback": provided.feedback if provided.feedback is not None else RISK_SIGNAL_NEUTRAL_DEFAULT,
        "confidence": finding.confidence,
    }
    return {name: _clamp(value) for name, value in resolved.items()}


def compute_risk_breakdown(finding: EnrichedFinding) -> Dict[str, float]:
    signals = resolve_signals(finding)
    breakdown = {}
    for name, weight in RISK_SIGNAL_WEIGHTS.items():
        breakdown[name] = round(signals.get(name, 0.0) * weight, 4)
    return breakdown


def compute_risk_score(finding: EnrichedFinding) -> int:
    breakdown = compute_risk_breakdown(finding)
    score = round(sum(breakdown.values()) * 100)
    return max(0, min(100, score))
