from __future__ import annotations

from typing import Any

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, MetadataContextMixin, RevisionMixin, SchemaVersionMixin


class ArenaSeasonReward(Base, MetadataContextMixin, SchemaVersionMixin, RevisionMixin):
    """Stub table for future season-end reward distribution.

    Populated by `arena.season_ended` hook; redemption logic TBD.
    """

    __tablename__ = "arena_season_rewards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("arena_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
