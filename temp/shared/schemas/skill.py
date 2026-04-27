from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.shared.enums.skill_enums import SkillProgressState


class SkillProgressDTO(BaseModel):
    """
    DTO для прогресса навыка.
    """

    character_id: int
    skill_key: str
    total_xp: float
    is_unlocked: bool
    progress_state: SkillProgressState  # Enum: PLUS, PAUSE, MINUS

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
