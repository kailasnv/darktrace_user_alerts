from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import DB_CONFIG


class Base(DeclarativeBase):
    pass


class AlertRecord(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    watchlist_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    finding_id: Mapped[str] = mapped_column(String(128), nullable=False)
    threat_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suppression_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    indicator_values: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    threat_actor_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    stix_export_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_required")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_alert_state", "state"),
        Index("idx_alert_threat_actor", "threat_actor_name"),
    )


class SuppressionRuleRecord(Base):
    __tablename__ = "suppression_rules"

    rule_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    threat_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    indicator_value: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EscalationLogRecord(Base):
    __tablename__ = "escalation_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    escalated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)

class AlertAuditRecord(Base):
    __tablename__ = "alert_audit"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    alert_id: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    actor_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    from_state: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )

    to_state: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )

    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )





class ExportAuditRecord(Base):
    __tablename__ = "stix_taxii_export_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    bundle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    object_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)





def record_alert_audit(
    session: Session,
    alert_id: str,
    action: str,
    actor_id: str,
    from_state: Optional[str] = None,
    to_state: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    session.add(
        AlertAuditRecord(
            alert_id=alert_id,
            action=action,
            actor_id=actor_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            created_at=datetime.now(),
        )
    )




_engine = create_engine(DB_CONFIG.url, echo=DB_CONFIG.echo, future=True)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(_engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
