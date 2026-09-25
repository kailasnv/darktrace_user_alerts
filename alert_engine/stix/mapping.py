from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from stix2 import (
    URL,
    DomainName,
    EmailAddress,
    File,
    IPv4Address,
    Identity,
    Indicator as StixIndicator,
    ObservedData,
    Relationship,
    ThreatActor,
)

from ..models import Alert, EnrichedFinding, Indicator

_SEVERITY_TO_CONFIDENCE = {
    "informational": 20,
    "low": 35,
    "medium": 55,
    "high": 75,
    "critical": 95,
}

_STIX_CYBER_OBSERVABLE_BUILDERS = {
    "email": lambda value: EmailAddress(value=value),
    "domain": lambda value: DomainName(value=value),
    "ip": lambda value: IPv4Address(value=value),
    "url": lambda value: URL(value=value),
    "file_hash": lambda value: File(hashes={"SHA-256": value} if len(value) == 64 else {"MD5": value}),
}

_STIX_PATTERN_BUILDERS = {
    "email": lambda value: f"[email-addr:value = '{value}']",
    "domain": lambda value: f"[domain-name:value = '{value}']",
    "ip": lambda value: f"[ipv4-addr:value = '{value}']",
    "url": lambda value: f"[url:value = '{value}']",
    "file_hash": lambda value: (
        f"[file:hashes.'SHA-256' = '{value}']" if len(value) == 64 else f"[file:hashes.MD5 = '{value}']"
    ),
    "credential": lambda value: f"[user-account:display_name = '{value}']",
    "cve": lambda value: f"[vulnerability:name = '{value}']",
}


def _build_pattern(indicator: Indicator) -> Optional[str]:
    builder = _STIX_PATTERN_BUILDERS.get(indicator.type)
    if builder is None:
        return None
    return builder(indicator.value)


def _build_observable(indicator: Indicator):
    builder = _STIX_CYBER_OBSERVABLE_BUILDERS.get(indicator.type)
    if builder is None:
        return None
    return builder(indicator.value)


def map_indicators(finding: EnrichedFinding, alert: Alert) -> List[StixIndicator]:
    stix_indicators: List[StixIndicator] = []
    severity_value = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
    confidence = _SEVERITY_TO_CONFIDENCE.get(severity_value, 50)

    for indicator in finding.indicators:
        pattern = _build_pattern(indicator)
        if pattern is None:
            continue
        stix_indicators.append(
            StixIndicator(
                name=f"{finding.threat_type}:{indicator.type}:{indicator.value}"[:250],
                description=f"Indicator observed via {finding.source_id} for finding {finding.finding_id}",
                pattern=pattern,
                pattern_type="stix",
                valid_from=alert.first_seen,
                confidence=confidence,
                indicator_types=[finding.threat_type.replace("_", "-")],
                labels=[severity_value],
            )
        )
    return stix_indicators


def map_observables(finding: EnrichedFinding) -> List[Any]:
    observables: List[Any] = []
    for indicator in finding.indicators:
        obj = _build_observable(indicator)
        if obj is not None:
            observables.append(obj)
    return observables


def map_observed_data(finding: EnrichedFinding, alert: Alert, observables: List[Any]) -> Optional[ObservedData]:
    if not observables:
        return None
    return ObservedData(
        first_observed=alert.first_seen,
        last_observed=alert.last_seen,
        number_observed=max(alert.count, 1),
        object_refs=[obj.id for obj in observables],
    )


def map_threat_actor(finding: EnrichedFinding) -> Optional[ThreatActor]:
    if not finding.threat_actor:
        return None
    name = finding.threat_actor.get("name")
    if not name:
        return None
    roles = finding.threat_actor.get("roles")
    goals = finding.threat_actor.get("goals")
    return ThreatActor(
        name=name,
        description=finding.threat_actor.get("description", ""),
        threat_actor_types=finding.threat_actor.get("types", ["unknown"]),
        roles=roles,
        goals=goals if goals else None,
        sophistication=finding.threat_actor.get("sophistication"),
    )


def map_relationships(
    indicators: List[StixIndicator],
    observed_data: Optional[ObservedData],
    threat_actor: Optional[ThreatActor],
) -> List[Relationship]:
    relationships: List[Relationship] = []
    for indicator in indicators:
        if observed_data is not None:
            relationships.append(
                Relationship(
                    relationship_type="based-on",
                    source_ref=indicator.id,
                    target_ref=observed_data.id,
                )
            )
        if threat_actor is not None:
            relationships.append(
                Relationship(
                    relationship_type="indicates",
                    source_ref=indicator.id,
                    target_ref=threat_actor.id,
                )
            )
    return relationships


def map_finding_to_stix_objects(finding: EnrichedFinding, alert: Alert) -> List[Any]:
    indicators = map_indicators(finding, alert)
    observables = map_observables(finding)
    observed_data = map_observed_data(finding, alert, observables)
    threat_actor = map_threat_actor(finding)
    relationships = map_relationships(indicators, observed_data, threat_actor)

    objects: List[Any] = list(indicators)
    objects.extend(observables)
    if observed_data is not None:
        objects.append(observed_data)
    if threat_actor is not None:
        objects.append(threat_actor)
    objects.extend(relationships)
    return objects
