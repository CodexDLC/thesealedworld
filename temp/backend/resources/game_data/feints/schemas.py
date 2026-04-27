from typing import Any

from pydantic import BaseModel, Field

from src.backend.resources.game_data.common.targeting import TargetType


class FeintCostDTO(BaseModel):
    """
    Стоимость финта (Tactical).
    """

    # Стоимость в тактических токенах (int, положительные числа).
    # Примеры: {"crit": 1, "hit": 2}
    tactics: dict[str, int] = Field(default_factory=dict)


class FeintConfigDTO(BaseModel):
    """
    Конфигурация финта (Tactical Move).
    """

    feint_id: str
    name_ru: str
    description_ru: str

    # === COST ===
    cost: FeintCostDTO = Field(default_factory=FeintCostDTO)

    # === TARGETING ===
    target: TargetType = TargetType.SINGLE_ENEMY
    target_count: int = 1

    # === PRE-CALC (Настройка удара) ===

    # 1. Прямое изменение статов (RAW) - Строки для WaterfallCalculator
    # Пример: {"physical_damage_bonus": "+10", "accuracy_mult": "-0.2"}
    raw_mutations: dict[str, str] | None = None

    # 2. Гарантированные флаги (Pipeline)
    # Пример: {"restriction.ignore_block": True}
    pipeline_mutations: dict[str, Any] | None = None

    # 3. Вероятностные и Реактивные правила (Triggers)
    # Список путей к флагам в TriggerRulesFlagsDTO
    # Пример: ["accuracy.true_strike", "dodge.counter_on_dodge"]
    triggers: list[str] | None = None

    # Полная замена урона (редко, но бывает)
    override_damage: tuple[float, float] | None = None

    # === POST-CALC (Последствия) ===

    # Наложение эффектов (обычно при попадании)
    # Пример: [{"id": "bleed", "params": {"power": 10}}]
    effects: list[dict[str, Any]] | None = None
