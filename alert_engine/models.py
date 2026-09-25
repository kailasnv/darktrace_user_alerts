from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Severity(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertState(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    DISMISSED = "dismissed"
    CLOSED = "closed"


class StixExportStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"
    FAILED = "failed"


class RiskSignals(BaseModel):
    keyword: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    classification: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    entities: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    history: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source_reputation: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    behavior: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    temporal: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    feedback: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class Indicator(BaseModel):
    type: str
    value: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("value")
    @classmethod
    def normalize_value(cls, v: str) -> str:
        return v.strip()


class EnrichedFinding(BaseModel):
    finding_id: str
    threat_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_id: str
    watchlist_id: Optional[str] = None
    tenant_id: Optional[str] = None
    indicators: List[Indicator] = Field(default_factory=list)
    threat_actor: Optional[Dict[str, Any]] = None
    signals: RiskSignals = Field(default_factory=RiskSignals)
    context: Dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime = Field(default_factory=utc_now)
    raw: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("threat_type")
    @classmethod
    def normalize_threat_type(cls, v: str) -> str:
        return v.strip().lower()


class RoutingDecision(BaseModel):
    channels: List[str] = Field(default_factory=list)
    policy_version: str = "v1"


class EscalationRecord(BaseModel):
    escalated_at: datetime
    reason: str
    level: int


class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fingerprint: str
    source_id: str
    watchlist_id: Optional[str] = None
    tenant_id: Optional[str] = None
    finding_id: str
    threat_type: str
    severity: Severity
    risk_score: int = Field(ge=0, le=100)
    confidence: float
    state: AlertState = AlertState.NEW
    first_seen: datetime
    last_seen: datetime
    count: int = 1
    indicators: List[Indicator] = Field(default_factory=list)
    threat_actor: Optional[Dict[str, Any]] = None
    routing: RoutingDecision = Field(default_factory=RoutingDecision)
    escalations: List[EscalationRecord] = Field(default_factory=list)
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    risk_breakdown: Dict[str, float] = Field(default_factory=dict)
    related_alert_ids: List[str] = Field(default_factory=list)
    stix_export_status: StixExportStatus = StixExportStatus.NOT_REQUIRED
    context: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": False}

    def to_channel_payload(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "fingerprint": self.fingerprint,
            "source_id": self.source_id,
            "watchlist_id": self.watchlist_id,
            "tenant_id": self.tenant_id,
            "severity": self.severity.value if isinstance(self.severity, Severity) else self.severity,
            "confidence": self.confidence,
            "state": self.state.value if isinstance(self.state, AlertState) else self.state,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "count": self.count,
            "threat_type": self.threat_type,
            "indicators": [i.model_dump() for i in self.indicators],
            "channels": self.routing.channels,
            "risk_breakdown": self.risk_breakdown,
            "risk_score": self.risk_score,
	    "related_alert_ids": self.related_alert_ids,
            "stix_export_status": (
                self.stix_export_status.value
                if isinstance(self.stix_export_status, StixExportStatus)
                else self.stix_export_status
            ),
        }


class SuppressionScope(BaseModel):
    source_id: Optional[str] = None
    tenant_id: Optional[str] = None
    threat_type: Optional[str] = None
    indicator_value: Optional[str] = None


class SuppressionRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scope: SuppressionScope
    reason: str
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    active: bool = True

    def is_expired(self, at: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        return (at or utc_now()) >= self.expires_at
