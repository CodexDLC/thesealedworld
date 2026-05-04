from typing import Any, TypedDict


class EffectParams(TypedDict, total=False):
    """
    Стандартная структура параметров для наложения эффекта.
    Используется в AbilityConfigDTO.effects, FeintConfigDTO.effects и TriggerDTO.mutations['add_effect'].
    Эти параметры передаются в EffectFactory для создания ActiveEffectDTO.
    """

    # === CORE ===
    duration: int  # Переопределяет config.duration.

    # === SCALING ===
    # Множитель силы. Применяется к config.resource_impact.
    # Default: 1.0.
    power: float

    # === STAT MUTATIONS ===
    # Изменение статов (RAW modifiers).
    # Эти мутации будут добавлены к config.raw_modifiers и применены к actor.raw.
    # Пример: {"strength": 10, "physical_damage_mult": "+0.5"}
    mutations: dict[str, Any]

    # === CONTROL FLAGS ===
    # Переопределение/дополнение config.control_logic.
    # Пример: {"source_behavior": {"can_act": False}}
    control: dict[str, Any]

    # === REMOVAL CONDITIONS ===
    # Условия снятия эффекта (помимо длительности).
    # Пример: ["is_hit", "is_crit"]
    remove_on: list[str]
