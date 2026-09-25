from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_event"

    seq: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    event_id: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )
    actor_usr: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    object_type: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    object_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    details: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    prev_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    entry_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
