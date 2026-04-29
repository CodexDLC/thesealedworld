from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.core.database import Base, TimestampMixin
from src.shared.enums.skill_enums import SkillProgressState

if TYPE_CHECKING:
    from src.backend.features.actor_state.models.character import Character


class SkillProgress(Base, TimestampMixin):
    __tablename__ = "character_skill_progress"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_key: Mapped[str] = mapped_column(String(50), nullable=False)
    total_xp: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_unlocked: Mapped[bool] = mapped_column(default=False, nullable=False)
    progress_state: Mapped[SkillProgressState] = mapped_column(
        Enum(SkillProgressState, name="skill_progress_state_enum", create_type=True),
        default=SkillProgressState.PAUSE,
        nullable=False,
    )

    character: Mapped[Character] = relationship("Character", back_populates="skill_progress")

    __table_args__ = (PrimaryKeyConstraint("character_id", "skill_key", name="pk_character_skill_progress"),)


CharacterSkillProgress = SkillProgress
