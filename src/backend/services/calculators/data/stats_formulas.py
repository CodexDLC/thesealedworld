"""
Модуль содержит правила для расчета производных характеристик (модификаторов)
на основе базовых характеристик персонажа.

СИНХРОНИЗИРОВАНО С: src/shared/enums/stats_enums.py
"""

from src.backend.features.character.runtime.vitals import (
    ENERGY_PER_MENTAL,
    ENERGY_REGEN_PER_MENTAL,
    HP_PER_ENDURANCE,
    HP_REGEN_PER_ENDURANCE,
    STAMINA_PER_ENDURANCE,
    STAMINA_REGEN_PER_ENDURANCE,
)
from src.shared.enums.stats_enums import StatKey

MODIFIER_RULES: dict[str, dict[str, float]] = {
    # ==========================================================================
    # ⚔️ 1. УРОН (Damage Base)
    # ==========================================================================
    # Сила дает чистый урон (Body)
    StatKey.PHYSICAL_DAMAGE: {StatKey.STRENGTH: 1.0},
    # ==========================================================================
    # 🎯 2. ТОЧНОСТЬ И ПРОБИТИЕ (Accuracy & Penetration)
    # ==========================================================================
    # Точность (Sensor: Perception + Prediction)
    StatKey.ACCURACY: {StatKey.PERCEPTION: 0.02, StatKey.PREDICTION: 0.01},
    # Пробивание брони (Sensor: Perception)
    StatKey.ARMOR_PENETRATION: {StatKey.PERCEPTION: 0.01},
    # ==========================================================================
    # 💥 3. КРИТ (Crit Chance)
    # ==========================================================================
    # Крит шанс (Sensor: Prediction - предвидение уязвимостей)
    StatKey.CRIT_CHANCE: {StatKey.PREDICTION: 0.02},
    # Крит сила (Core: Memory - знание анатомии/слабостей)
    StatKey.CRIT_POWER: {StatKey.MEMORY: 0.01},
    # ==========================================================================
    # 🛡️ 4. ЗАЩИТА (Defense)
    # ==========================================================================
    # Уворот (Body: Agility + Sensor: Prediction)
    StatKey.EVASION: {StatKey.AGILITY: 0.015, StatKey.PREDICTION: 0.005},
    # Броня (Body: Endurance)
    StatKey.ARMOR: {StatKey.ENDURANCE: 0.5},
    # Блок (Body: Strength)
    StatKey.BLOCK: {StatKey.STRENGTH: 0.02},
    # Парирование (Body: Agility)
    StatKey.PARRY: {StatKey.AGILITY: 0.02},
    # ==========================================================================
    # 🔮 5. МАГИЯ (Magic)
    # ==========================================================================
    # Маг. урон (Core: Intellect)
    StatKey.MAGICAL_DAMAGE: {StatKey.INTELLECT: 1.0},
    # Маг. резист (Core: Mental)
    StatKey.MAGIC_RESIST: {StatKey.MENTAL: 0.01},
    # ==========================================================================
    # 💀 6. РЕСУРСЫ (Vitals)
    # ==========================================================================
    # HP (Body: Endurance)
    StatKey.HP: {StatKey.ENDURANCE: HP_PER_ENDURANCE},
    # EN (Core: Mental)
    StatKey.EN: {StatKey.MENTAL: ENERGY_PER_MENTAL},
    # Stamina (Body: Endurance)
    StatKey.STAMINA: {StatKey.ENDURANCE: STAMINA_PER_ENDURANCE},
    # Реген
    StatKey.HP_REGEN: {StatKey.ENDURANCE: HP_REGEN_PER_ENDURANCE},
    StatKey.EN_REGEN: {StatKey.MENTAL: ENERGY_REGEN_PER_MENTAL},
    StatKey.STAMINA_REGEN: {StatKey.ENDURANCE: STAMINA_REGEN_PER_ENDURANCE},
    # ==========================================================================
    # ⚡ 7. СКОРОСТЬ (Speed)
    # ==========================================================================
    # Инициатива (Sensor: Prediction + Body: Agility)
    StatKey.INITIATIVE: {StatKey.PREDICTION: 1.0, StatKey.AGILITY: 0.5},
    # Скорость атаки (Body: Agility)
    StatKey.ATTACK_SPEED: {StatKey.AGILITY: 0.005},
    # Скорость каста (Core: Memory - мышечная память формул)
    StatKey.CAST_SPEED: {StatKey.MEMORY: 0.005},
    # Скорость движения (Body: Agility)
    StatKey.MOVEMENT_SPEED: {StatKey.AGILITY: 0.01},
    # ==========================================================================
    # 🎭 8. СОЦИАЛКА И ПРОЧЕЕ (Misc)
    # ==========================================================================
    # Проекция (Влияние/Харизма) влияет на торговлю? Пока оставим пустым или привяжем к Projection
    # "trade_discount": {StatKey.PROJECTION: 0.01},
}

DEFAULT_VALUES = {
    "dodge_cap": 0.75,
    "resistance_cap": 0.85,
    "shield_block_cap": 0.75,
    "parry_cap": 0.50,
    "counter_attack_cap": 0.50,
    "vampiric_trigger_cap": 1.0,
    "spell_land_chance": 1.0,
}
