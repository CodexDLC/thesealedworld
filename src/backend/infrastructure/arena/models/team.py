from __future__ import annotations

import datetime as dt  # noqa: TC003

from sqlalchemy import BigInteger, DateTime, ForeignKey, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, MetadataContextMixin, RevisionMixin, SchemaVersionMixin, TimestampMixin


class ArenaTeam(Base, TimestampMixin, MetadataContextMixin, SchemaVersionMixin, RevisionMixin):
    __tablename__ = "arena_teams"
    __table_args__ = (UniqueConstraint("leader_id", "name", name="uq_arena_teams_leader_name"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    leader_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(48), nullable=False)
    size: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)


class ArenaTeamMembership(Base, MetadataContextMixin, SchemaVersionMixin):
    __tablename__ = "arena_team_members"

    team_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("arena_teams.id", ondelete="CASCADE"),
        primary_key=True,
    )
    char_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)
    joined_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
