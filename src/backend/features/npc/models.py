from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base


class CharacterNpcState(Base):
    __tablename__ = "character_npc_states"
    __table_args__ = (UniqueConstraint("character_id", "npc_key", name="uq_character_npc_states_character_npc"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    npc_key: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    reputation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    affinity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flags: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    counters: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CharacterNpcEffectLog(Base):
    __tablename__ = "character_npc_effect_logs"
    __table_args__ = (
        UniqueConstraint(
            "character_id",
            "npc_key",
            "idempotency_key",
            name="uq_character_npc_effect_logs_character_npc_idempotency",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    npc_key: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    effect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
