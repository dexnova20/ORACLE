"""Diagnostic run persistence entity model."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from oracle.db.base import Base


class DiagnosticRunState(str, enum.Enum):
    """Lifecycle status for a diagnostic run."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class DiagnosticRunRecord(Base):
    """Represents a diagnostic run record in the ORACLE database."""

    __tablename__ = "diagnostic_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=DiagnosticRunState.COMPLETED.value,
        nullable=False,
        index=True,
    )
    commit_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    summary: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    report_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    duration_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("status", DiagnosticRunState.COMPLETED.value)
        kwargs.setdefault("duration_ms", 0.0)
        super().__init__(**kwargs)
