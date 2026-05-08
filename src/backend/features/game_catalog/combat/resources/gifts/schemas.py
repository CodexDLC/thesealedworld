from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatCatalogEntryDTO,
    CombatDescriptionDTO,
    CombatEventTextSetDTO,
    build_combat_description,
)


class GiftSchool(StrEnum):
    FIRE = "fire"
    WATER = "water"
    AIR = "air"
    EARTH = "earth"
    LIGHT = "light"
    DARKNESS = "darkness"
    NATURE = "nature"
    ARCANE = "arcane"


class GiftTechnicalDTO(BaseModel):
    gift_id: str
    school: GiftSchool
    role: str

    # Пока простая структура, как в исходном файле, но готовая к расширению
    abilities: list[str] = Field(default_factory=list)

    # Задел на будущее (прогрессия)
    abilities_progression: dict[int, list[str]] = Field(default_factory=dict)

    effects: list[dict[str, Any]] | None = None
    triggers: list[str] | None = None
    token_grants: dict[str, int] | None = None


class GiftCatalogEntryDTO(CombatCatalogEntryDTO):
    key: str
    technical: GiftTechnicalDTO
    descriptive: CombatDescriptionDTO


GiftDTO = GiftTechnicalDTO


def build_gift_catalog_entry(
    *,
    technical: GiftTechnicalDTO,
    display_name: str,
    short_description: str,
    icon: str | None = None,
    event_texts: CombatEventTextSetDTO | None = None,
) -> GiftCatalogEntryDTO:
    return GiftCatalogEntryDTO(
        key=f"combat.gift.{technical.gift_id}",
        technical=technical,
        descriptive=build_combat_description(
            resource_type="gifts",
            resource_id=technical.gift_id,
            icon=icon or f"combat/gifts/{technical.gift_id}.svg",
            display_name=display_name,
            short_description=short_description,
            humanoid_long_description=short_description,
            humanoid_event_texts=event_texts
            or CombatEventTextSetDTO(
                use=["Дар {gift} отзывается на волю {source}."],
                no_resource=["Дар {gift} не отзывается: {source} не хватает ресурса."],
            ),
            beast_event_texts=CombatEventTextSetDTO(),
        ),
    )
