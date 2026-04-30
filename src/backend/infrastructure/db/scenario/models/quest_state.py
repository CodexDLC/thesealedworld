from __future__ import annotations

import uuid  # noqa: TC003
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.backend.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    import uuid


class CharacterQuestState(Base, TimestampMixin):
    __tablename__ = "character_quest_state"

    character_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        primary_key=True,
    )
    quest_key: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("scenario_master.quest_key", ondelete="CASCADE"),
        nullable=False,
    )
    node_key: Mapped[str] = mapped_column(String(50), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
