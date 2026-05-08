from pydantic import BaseModel, Field

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatCatalogEntryDTO,
    CombatDescriptionDTO,
)


class BasicExchangeTechnicalDTO(BaseModel):
    exchange_id: str
    skill_key: str
    source_type: str
    weapon_class: str
    hand: str
    trigger_keys: list[str] = Field(default_factory=list)


class BasicExchangeCatalogEntryDTO(CombatCatalogEntryDTO):
    technical: BasicExchangeTechnicalDTO
    descriptive: CombatDescriptionDTO
