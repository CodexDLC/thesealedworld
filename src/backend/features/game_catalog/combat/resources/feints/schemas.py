from typing import Literal

from pydantic import BaseModel, Field

from src.backend.features.game_catalog.combat.resources.common.descriptions import (
    CombatCatalogEntryDTO,
    CombatDescriptionDTO,
)
from src.backend.features.game_catalog.combat.resources.common.modifier_applications import ModifierApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import PipelineMutationApplicationDTO
from src.backend.features.game_catalog.combat.resources.common.targeting import TargetType


class FeintCostDTO(BaseModel):
    """
    Стоимость финта (Tactical).
    """

    # Стоимость в тактических токенах (int, положительные числа).
    # Примеры: {"crit": 1, "hit": 2}
    tactics: dict[str, int] = Field(default_factory=dict)


class FeintTechnicalDTO(BaseModel):
    """
    Technical configuration for a feint.

    Feints are exchange-only attack modifiers: they are selected together with
    an attack target and change the exchange pipeline. Standalone instant
    actions belong to abilities, effects, or items, not to feints.
    """

    feint_id: str

    # === COST ===
    cost: FeintCostDTO = Field(default_factory=FeintCostDTO)

    # === TARGETING ===
    target: TargetType = TargetType.SINGLE_ENEMY
    target_count: int = 1

    # === PRE-CALC (Настройка удара) ===

    # 1. Numeric stat changes compiled through modifier contracts into raw.temp.
    modifier_applications: list[ModifierApplicationDTO] = Field(default_factory=list)

    # 2. Whitelisted pipeline-local context/result mutations.
    pipeline_mutations: list[PipelineMutationApplicationDTO] = Field(default_factory=list)

    # 3. Вероятностные и Реактивные правила (Triggers)
    # Список путей к флагам в TriggerRulesFlagsDTO
    # Пример для будущего набора: ["accuracy.some_feint_rule"]
    triggers: list[str] | None = None

    # Catalog tags used by weapon/style mappers.
    applicability_tags: list[str] = Field(default_factory=list)

    # Purchase group used by FeintService to reserve one preferred feint per hand slot type.
    purchase_group: Literal["basic", "weapon", "tactical"] = "basic"

    # Weapon technique flat damage added only when the exchange reaches damage calculation.
    hit_damage_bonus_per_tier: float = 0.0

    # Shield technique damage derived from the acting shield guard power.
    shield_guard_damage_ratio: float = 0.0
    shield_guard_damage_min: int = 0
    shield_guard_damage_tier_fallback: int = 0

    # Полная замена урона (редко, но бывает)
    override_damage: tuple[float, float] | None = None

    # === POST-CALC (Последствия) ===

    # Наложение эффектов (обычно при попадании)
    # Пример: [{"id": "bleed", "params": {"power": 10}}]
    effects: list[dict] | None = None

    # Подготовки/бафы, которые накладываются после выбранной атаки независимо
    # от попадания: например следующий уворот или парирование открывает контратаку.
    preparation_effects: list[dict] | None = None


class FeintCatalogEntryDTO(CombatCatalogEntryDTO):
    technical: FeintTechnicalDTO
    descriptive: CombatDescriptionDTO


class FeintRenderContextDTO(BaseModel):
    template: str
    event: str
    taxonomy: str = "humanoid"
    variant: int = 0
    variables: dict[str, str | int | float] = Field(default_factory=dict)
