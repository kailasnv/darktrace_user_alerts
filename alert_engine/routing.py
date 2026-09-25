from __future__ import annotations

from .config import ROUTING_POLICY
from .models import RoutingDecision, Severity


def decide_routing(severity: Severity) -> RoutingDecision:
    channels = ROUTING_POLICY.get(severity.value, [])
    return RoutingDecision(channels=list(channels), policy_version="v1")
