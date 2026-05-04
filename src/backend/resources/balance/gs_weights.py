"""
НОРМАЛИЗАТОРЫ ХАРАКТЕРИСТИК ДЛЯ GEAR SCORE
=========================================

Этот файл содержит делители (`divisor`) для расчета Gear Score (GS).
GS рассчитывается ИСКЛЮЧИТЕЛЬНО на основе модификаторов персонажа.

ВАЖНО: При добавлении нового модификатора в `modifier_dto.py`, его ОБЯЗАТЕЛЬНО
нужно добавить сюда. Для мирных или не влияющих на GS статов используется `divisor: 0.0`.

Формула для каждого стата:
    stat_gs = stat_value / divisor
"""

# Ключ - название модификатора, значение - делитель.
# Если делитель 0.0, стат не учитывается в GS.
GS_DIVISORS: dict[str, float] = {
    # --- РЕСУРСЫ ---
    "hp_max": 10.0,  # Каждые 10 HP = 1 GS
    "hp_regen": 1.0,
    "energy_max": 5.0,
    "energy_regen": 1.0,
    "resource_cost_reduction": 0.01,
    # --- ФИЗИЧЕСКАЯ АТАКА ---
    "physical_damage_min": 0.0,
    "physical_damage_max": 0.0,
    "physical_damage_bonus": 0.01,
    "physical_penetration": 0.01,
    "physical_accuracy": 0.01,
    "physical_crit_chance": 0.01,
    "physical_crit_power_float": 0.01,
    "physical_pierce_chance": 0.01,
    "physical_crit_cap": 0.0,
    # --- МАГИЧЕСКАЯ АТАКА ---
    "magical_damage_power": 1.0,
    "magical_damage_bonus": 0.01,
    "magical_penetration": 0.01,
    "magical_accuracy": 0.01,
    "spell_land_chance": 0.0,
    "magical_crit_chance": 0.01,
    "magical_crit_power_float": 0.01,
    "magical_crit_cap": 0.0,
    # --- ЗАЩИТА ---
    "physical_resistance": 0.01,
    "magical_resistance": 0.01,
    "damage_reduction_flat": 1.0,
    "resistance_cap": 0.0,
    "dodge_chance": 0.01,
    "dodge_cap": 0.0,
    "debuff_avoidance": 0.01,
    "parry_chance": 0.01,
    "parry_cap": 0.0,
    "shield_block_chance": 0.01,
    "shield_block_power": 0.01,
    "shield_block_cap": 0.0,
    "anti_crit_chance": 0.01,
    "anti_dodge_chance": 0.01,
    "anti_physical_crit_chance": 0.01,
    "anti_magical_crit_chance": 0.01,
    "control_resistance": 0.01,
    "shock_resistance": 0.01,
    # --- СТИХИИ ---
    "fire_damage_bonus": 0.01,
    "fire_resistance": 0.01,
    "water_damage_bonus": 0.01,
    "water_resistance": 0.01,
    "air_damage_bonus": 0.01,
    "air_resistance": 0.01,
    "earth_damage_bonus": 0.01,
    "earth_resistance": 0.01,
    "light_damage_bonus": 0.01,
    "light_resistance": 0.01,
    "dark_damage_bonus": 0.01,
    "dark_resistance": 0.01,
    "poison_damage_bonus": 0.01,
    "poison_resistance": 0.01,
    "poison_efficiency": 0.01,
    "bleed_damage_bonus": 0.01,
    "bleed_resistance": 0.01,
    "thorns_damage_reflect": 0.01,
    # --- СПЕЦИАЛЬНЫЕ ---
    "counter_attack_chance": 0.01,
    "vampiric_power": 0.01,
    "vampiric_trigger_chance": 0.01,
    "healing_power": 0.01,
    "received_healing_bonus": 0.01,
    "pet_damage_bonus": 0.0,
    "pet_health_bonus": 0.0,
    # --- СРЕДА ---
    "environment_cold_resistance": 0.0,
    "environment_heat_resistance": 0.0,
    "environment_gravity_resistance": 0.0,
    "environment_bio_resistance": 0.0,
    # --- МИРНЫЕ ---
    "trade_discount": 0.0,
    "find_loot_chance": 0.0,
    "crafting_success_chance": 0.0,
    "crafting_critical_chance": 0.0,
    "crafting_speed": 0.0,
    "skill_gain_bonus": 0.0,
    "inventory_slots_bonus": 0.0,
    "weight_limit_bonus": 0.0,
}
