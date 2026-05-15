from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, RevisionMixin, SchemaVersionMixin


class AIGenerationTask(Base, SchemaVersionMixin, RevisionMixin):
    __tablename__ = "ai_generation_tasks"
    __table_args__ = (
        UniqueConstraint(
            "identity_key",
            name="uq_ai_generation_task_identity_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    identity_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    season_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    output_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    asset_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    storage_prefix: Mapped[str | None] = mapped_column(String(240), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    generated_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    prompt_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    error: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
