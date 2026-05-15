from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Integer, MetaData, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)


class SchemaVersionMixin:
    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class RevisionMixin:
    revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def bump_revision(self) -> int:
        self.revision = int(self.revision or 0) + 1
        return self.revision


class LifecycleStatusMixin:
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    def mark_archived(self, *, at: datetime | None = None) -> None:
        self.lifecycle_status = "archived"
        self.archived_at = at or datetime.now(UTC)

    def is_expired(self, *, at: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return self.expires_at <= (at or datetime.now(UTC))


class MetadataContextMixin:
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    source_context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    def merge_metadata(self, values: dict[str, Any]) -> dict[str, Any]:
        self.metadata_ = {**dict(self.metadata_ or {}), **values}
        return self.metadata_

    def merge_context(self, values: dict[str, Any]) -> dict[str, Any]:
        self.context = {**dict(self.context or {}), **values}
        return self.context

    def merge_source_context(self, values: dict[str, Any]) -> dict[str, Any]:
        self.source_context = {**dict(self.source_context or {}), **values}
        return self.source_context


class ContextSourceMixin:
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    source_context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    def merge_context(self, values: dict[str, Any]) -> dict[str, Any]:
        self.context = {**dict(self.context or {}), **values}
        return self.context

    def merge_source_context(self, values: dict[str, Any]) -> dict[str, Any]:
        self.source_context = {**dict(self.source_context or {}), **values}
        return self.source_context
