"""Repository domain entity model."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from oracle.db.base import Base


class SourceType(str, enum.Enum):
    """Supported source repository types."""

    GIT = "git"
    LOCAL_DIRECTORY = "local_directory"


class RepositoryStatus(str, enum.Enum):
    """Lifecycle status for a registered repository."""

    REGISTERED = "registered"
    ARCHIVED = "archived"


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Repository(Base):
    """Represents a registered software repository / diagnostic target.

    Stores only metadata required to identify and address the target.
    Credentials, tokens, and cloned contents are strictly prohibited from persistence.
    """

    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        default=SourceType.GIT.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=RepositoryStatus.REGISTERED.value,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("source_type", SourceType.GIT.value)
        kwargs.setdefault("status", RepositoryStatus.REGISTERED.value)
        kwargs.setdefault("created_at", utc_now())
        kwargs.setdefault("updated_at", utc_now())
        super().__init__(**kwargs)
