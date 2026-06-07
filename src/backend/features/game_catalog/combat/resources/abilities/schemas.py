from typing import Any

from pydantic import BaseModel, Field

from src.backend.features.game_catalog.combat.resources.abilities.enums import AbilitySource, AbilityType
from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatCatalogEntryDTO,
    CombatDescriptionDTO,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import PipelineMutationApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType


class AbilityCostDTO(BaseModel):
    """
    Стоимость абилки.
    """

    energy: int = 0  # Мана / Энергия
    stamina: int = 0  # Выносливость
    hp: int = 0  # Здоровье (Кровавая магия)
    gift_tokens: int = 0  # Спец. ресурс Дара
    tokens: dict[str, int] = Field(default_factory=dict)  # Боевые токены: tempo, blood, hit, crit, etc.


class PipelineMutationsDTO(BaseModel):
    """
    Настройка Пайплайна для абилки.
    """

    preset: str | None = None  # Имя пресета (MAGIC_ATTACK, HEALING...)
    applications: list[PipelineMutationApplicationDTO] = Field(default_factory=list)


class AbilityTechnicalDTO(BaseModel):
    """
    Technical configuration for an active ability.
    """

    ability_id: str

    source: AbilitySource = AbilitySource.GIFT
    type: AbilityType = AbilityType.INSTANT

    # === COST ===
    cost: AbilityCostDTO = Field(default_factory=AbilityCostDTO)
    cooldown_exchanges: int | None = None

    # === TARGETING ===
    target: TargetType = TargetType.SINGLE_ENEMY
    target_count: int = 1
    secondary_damage_mult: float = 0.5

    # === PIPELINE CONFIG ===

    # 1. Numeric stat changes compiled through modifier contracts into raw.temp.
    modifier_applications: list[ModifierApplicationDTO] = Field(default_factory=list)

    # 2. Настройка Пайплайна (пресеты + whitelisted technical mutations)
    pipeline_mutations: PipelineMutationsDTO | None = None

    # 3. Активация Триггеров (ссылки на TRIGGER_RULES)
    # Пример: ["crit.burn_on_crit"]
    triggers: list[str] | None = None

    # 4. Полная замена урона (или хила)
    override_damage: tuple[float, float] | None = None

    # === EFFECTS ===

    # Наложение эффектов (Баффы, Дебаффы, Хил)
    # Пример: [{"id": "burn", "params": {"duration": 3}}]
    effects: list[dict[str, Any]] | None = None

    # Future: tokens granted by the action, separate from resolver-generated tokens.
    token_grants: dict[str, int] | None = None

    # Stable semantic hints for AI scoring and reports. They do not change runtime math.
    ai_tags: list[str] = Field(default_factory=list)

    # Placeholder multiplier. Runtime currently defaults to 1.0; later this can
    # be resolved from symbiote tier data before applying scaled modifiers.
    symbiote_ability_mult: float = 1.0


class AbilityCatalogEntryDTO(CombatCatalogEntryDTO):
    key: str
    technical: AbilityTechnicalDTO
    descriptive: CombatDescriptionDTO


# Compatibility import name for existing runtime code. This is the technical
# DTO, not the old text-bearing config shape.
AbilityConfigDTO = AbilityTechnicalDTO
