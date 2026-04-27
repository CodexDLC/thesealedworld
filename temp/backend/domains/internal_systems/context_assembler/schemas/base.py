import time
from typing import Any

from src.shared.schemas.character import CharacterAttributesReadDTO, CharacterReadDTO
from src.shared.schemas.skill import SkillProgressDTO
from pydantic import BaseModel, computed_field


class BaseTempContext(BaseModel):
    """
    Базовый контекст. Содержит сырые данные (Core Fields).
    Эти поля используются ТОЛЬКО для генерации проекций и НЕ сохраняются в Redis.
    """

    # === CORE DATA (Internal Only) ===
    core_attributes: CharacterAttributesReadDTO | None = None
    core_inventory: list[Any] | None = None  # List[InventoryItemDTO]
    core_skills: list[SkillProgressDTO] | None = None
    core_vitals: dict[str, Any] | None = None
    core_meta: CharacterReadDTO | None = None
    core_symbiote: dict[str, Any] | None = None
    core_wallet: dict[str, Any] | None = None

    # === COMPUTED FIELDS (Redis Output) ===

    @computed_field(alias="meta")
    def meta_view(self) -> dict[str, Any]:
        """
        Базовая мета-информация.
        """
        if not self.core_meta:
            return {"entity_id": 0, "type": "unknown", "timestamp": 0}

        return {
            "entity_id": self.core_meta.character_id,
            "type": "player",
            "name": self.core_meta.name,
            "timestamp": int(time.time()),
        }
