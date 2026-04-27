from typing import Any

from pydantic import BaseModel, Field

from src.backend.resources.game_data.abilities.enums import AbilitySource, AbilityType
from src.backend.resources.game_data.common.targeting import TargetType


class AbilityCostDTO(BaseModel):
    """
    Стоимость абилки.
    """

    energy: int = 0  # Мана / Энергия
    hp: int = 0  # Здоровье (Кровавая магия)
    gift_tokens: int = 0  # Спец. ресурс Дара


class PipelineMutationsDTO(BaseModel):
    """
    Настройка Пайплайна для абилки.
    """

    preset: str | None = None  # Имя пресета (MAGIC_ATTACK, HEALING...)
    flags: dict[str, Any] = Field(default_factory=dict)  # Индивидуальные флаги


class AbilityConfigDTO(BaseModel):
    """
    Конфигурация абилки (Gift Ability).
    """

    ability_id: str
    name_ru: str
    description_ru: str

    source: AbilitySource = AbilitySource.GIFT
    type: AbilityType = AbilityType.INSTANT

    # === COST ===
    cost: AbilityCostDTO = Field(default_factory=AbilityCostDTO)

    # === TARGETING ===
    target: TargetType = TargetType.SINGLE_ENEMY
    target_count: int = 1

    # === PIPELINE CONFIG ===

    # 1. Прямое изменение статов (RAW) - Строки для калькулятора
    # Пример: {"magical_damage_bonus": "*2.0"}
    raw_mutations: dict[str, str] | None = None

    # 2. Настройка Пайплайна (Пресеты + Флаги)
    # Пример: {"preset": "MAGIC_ATTACK", "flags": {"damage.fire": True}}
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
