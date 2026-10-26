"""Repository validation and serialization schemas."""

import re
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from oracle.models.repository import RepositoryStatus, SourceType

# Supported URL scheme regex: http, https, git, ssh, file
URL_SCHEME_REGEX = re.compile(r"^(https?|git|ssh|file)://", re.IGNORECASE)


class RepositoryCreate(BaseModel):
    """Payload schema for registering a new repository diagnostic target."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable repository name",
        examples=["my-service-repo"],
    )
    url: str = Field(
        ...,
        min_length=3,
        max_length=1024,
        description="Repository remote URL or local path with supported scheme",
        examples=["https://github.com/example/repo.git"],
    )
    source_type: SourceType = Field(
        default=SourceType.GIT,
        description="Source VCS type or directory layout",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Repository name cannot be empty or blank whitespace.")
        return trimmed

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Repository URL cannot be empty.")
        if not URL_SCHEME_REGEX.match(trimmed):
            raise ValueError(
                "Invalid repository URL scheme. Must start with http://, https://, git://, ssh://, or file://"
            )
        # Prevent malformed / scheme-only URLs (e.g., "https://")
        scheme_and_rest = URL_SCHEME_REGEX.sub("", trimmed)
        if not scheme_and_rest.strip():
            raise ValueError("Repository URL is incomplete or missing a host/path.")
        return trimmed


class RepositoryResponse(BaseModel):
    """Response schema for a registered repository."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique identifier for the repository")
    name: str = Field(..., description="Human-readable repository name")
    url: str = Field(..., description="Repository URL or location")
    source_type: str = Field(..., description="Source type (e.g. git)")
    status: str = Field(..., description="Lifecycle status (e.g. registered)")
    created_at: datetime = Field(..., description="UTC registration timestamp")
    updated_at: datetime = Field(..., description="UTC last updated timestamp")
