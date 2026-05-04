"""
РУКОВОДСТВО ПО ЗАПОЛНЕНИЮ: БРОНЯ
================================

Этот файл содержит шаблоны для физической брони (Heavy, Medium, Light).

КЛЮЧЕВЫЕ ПОЛЯ:
---------------
- slot: 'head_armor', 'chest_armor', 'arms_armor', 'legs_armor', 'feet_armor'.
- defense_type: 'physical' (для основной брони) или 'magical' (для брони магов).
- base_power: Показатель защиты (идет в damage_reduction_flat).
- implicit_bonuses: Врожденные бонусы (резисты, уворот, реген и т.д.).
- related_skill: Навык, отвечающий за владение этим предметом (XP, бонусы, штрафы).
"""

from typing import Any

from src.backend.resources.game_data.items.schemas import BaseItemDTO

ARMOR_DB: dict[str, BaseItemDTO | dict[str, Any]] = {
    # ==========================================
    # Тяжелая Броня (Plate)
    # Философия: "Танк". Максимум защиты, штрафы к мобильности.
    # Skill: heavy_armor
    # ==========================================
    "helmet": BaseItemDTO(
        id="helmet",
        name_ru="Шлем",
        slot="head_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["ingots"],
        base_power=4,
        base_durability=60,
        damage_spread=0.0,
        narrative_tags=["helmet", "visor", "protection"],
        implicit_bonuses={
            "anti_crit_chance": 0.10,  # Защита головы от критов
            "physical_resistance": 0.02,
        },
    ),
    "plate_chest": BaseItemDTO(
        id="plate_chest",
        name_ru="Кираса",
        slot="chest_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["ingots"],
        base_power=10,
        base_durability=100,
        damage_spread=0.0,
        narrative_tags=["plate", "heavy", "metal"],
        implicit_bonuses={
            "physical_resistance": 0.10,  # Основная броня
            "dodge_chance": -0.15,  # Тяжелая
            "thorns_damage_flat": 2.0,  # Шипы
        },
    ),
    "gauntlets": BaseItemDTO(
        id="gauntlets",
        name_ru="Латные рукавицы",
        slot="arms_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["ingots"],
        base_power=3,
        base_durability=70,
        damage_spread=0.0,
        narrative_tags=["gauntlets", "heavy", "fist"],
        implicit_bonuses={
            "physical_damage_bonus": 0.05,  # Утяжеление удара
            "physical_resistance": 0.02,
        },
    ),
    "greaves": BaseItemDTO(
        id="greaves",
        name_ru="Поножи",
        slot="legs_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["ingots"],
        base_power=5,
        base_durability=80,
        damage_spread=0.0,
        narrative_tags=["greaves", "shin_guard"],
        implicit_bonuses={
            "physical_resistance": 0.05,
            "dodge_chance": -0.05,
        },
    ),
    "sabatons": BaseItemDTO(
        id="sabatons",
        name_ru="Латные сапоги",
        slot="feet_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["ingots"],
        base_power=3,
        base_durability=70,
        damage_spread=0.0,
        narrative_tags=["sabatons", "heavy_boots"],
        implicit_bonuses={
            "shock_resistance": 0.20,  # Устойчивость
            "physical_resistance": 0.02,
        },
    ),
    # ==========================================
    # Средняя Броня (Leather / Chain)
    # Философия: "Баланс". Защита + Точность/Крит.
    # Skill: medium_armor
    # ==========================================
    "leather_cap": BaseItemDTO(
        id="leather_cap",
        name_ru="Кожаный шлем",
        slot="head_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["leathers"],
        base_power=2,
        base_durability=40,
        damage_spread=0.0,
        narrative_tags=["cap", "leather"],
        implicit_bonuses={
            "physical_accuracy": 0.05,  # Не мешает обзору
            "perception": 1.0,
        },
    ),
    "goggles": BaseItemDTO(
        id="goggles",
        name_ru="Защитные очки",
        slot="head_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["leathers", "ingots"],
        base_power=1,
        base_durability=30,
        damage_spread=0.0,
        narrative_tags=["goggles", "engineer", "vision"],
        implicit_bonuses={
            "physical_accuracy": 0.10,
            "perception": 2.0,
        },
    ),
    "jerkin": BaseItemDTO(
        id="jerkin",
        name_ru="Куртка",
        slot="chest_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["leathers"],
        base_power=6,
        base_durability=60,
        damage_spread=0.0,
        narrative_tags=["jacket", "vest", "scout"],
        implicit_bonuses={
            "dodge_chance": 0.05,  # Мобильность
            "physical_crit_chance": 0.05,  # Свобода движений
            "bleed_resistance": 0.10,
        },
    ),
    "leather_vest": BaseItemDTO(
        id="leather_vest",
        name_ru="Кожаный жилет",
        slot="chest_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["leathers"],
        base_power=4,
        base_durability=50,
        damage_spread=0.0,
        narrative_tags=["vest", "light", "leather"],
        implicit_bonuses={
            "dodge_chance": 0.05,
        },
    ),
    "bracers": BaseItemDTO(
        id="bracers",
        name_ru="Наручи",
        slot="arms_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["leathers"],
        base_power=2,
        base_durability=45,
        damage_spread=0.0,
        narrative_tags=["bracers", "wrist_guard"],
        implicit_bonuses={
            "physical_accuracy": 0.05,
            "parry_chance": 0.05,  # Удобно парировать
        },
    ),
    "breeches": BaseItemDTO(
        id="breeches",
        name_ru="Штаны",
        slot="legs_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["leathers"],
        base_power=3,
        base_durability=50,
        damage_spread=0.0,
        narrative_tags=["pants", "leather"],
        implicit_bonuses={
            "dodge_chance": 0.03,
            "inventory_slots_bonus": 1,  # Карманы
        },
    ),
    "boots": BaseItemDTO(
        id="boots",
        name_ru="Сапоги",
        slot="feet_armor",
        type="armor",
        defense_type="physical",
        allowed_materials=["leathers"],
        base_power=2,
        base_durability=50,
        damage_spread=0.0,
        narrative_tags=["boots", "travel"],
        implicit_bonuses={
            "dodge_chance": 0.05,
            "counter_attack_chance": 0.05,  # Работа ног
        },
    ),
    # ==========================================
    # Легкая Броня (Cloth)
    # Философия: "Магия и Уворот". Реген, Маг. защита, Спецэффекты.
    # Skill: light_armor
    # ==========================================
    "hood": BaseItemDTO(
        id="hood",
        name_ru="Капюшон",
        slot="head_armor",
        type="armor",
        defense_type="magical",
        allowed_materials=["cloths"],
        base_power=1,
        base_durability=30,
        damage_spread=0.0,
        narrative_tags=["hood", "mage_hat"],
        implicit_bonuses={
            "magical_resistance": 0.05,
            "debuff_avoidance": 0.05,  # Мистическая защита
        },
    ),
    "robe": BaseItemDTO(
        id="robe",
        name_ru="Мантия",
        slot="chest_armor",
        type="armor",
        defense_type="magical",
        allowed_materials=["cloths"],
        base_power=2,
        base_durability=40,
        damage_spread=0.0,
        narrative_tags=["robe", "wizard", "cloth"],
        implicit_bonuses={
            "magical_resistance": 0.10,
            "energy_regen": 1.5,  # Концентрация
            "dodge_chance": 0.05,
        },
    ),
    "wraps": BaseItemDTO(
        id="wraps",
        name_ru="Обмотки",
        slot="arms_armor",
        type="armor",
        defense_type="magical",
        allowed_materials=["cloths"],
        base_power=1,
        base_durability=25,
        damage_spread=0.0,
        narrative_tags=["wraps", "bandages"],
        implicit_bonuses={
            "healing_power": 0.05,  # Бонус к лечению
            "magical_accuracy": 0.05,
        },
    ),
    "leggings": BaseItemDTO(
        id="leggings",
        name_ru="Леггинсы",
        slot="legs_armor",
        type="armor",
        defense_type="magical",
        allowed_materials=["cloths"],
        base_power=1,
        base_durability=30,
        damage_spread=0.0,
        narrative_tags=["leggings", "cloth"],
        implicit_bonuses={
            "magical_resistance": 0.05,
            "dodge_chance": 0.05,
        },
    ),
    "sandals": BaseItemDTO(
        id="sandals",
        name_ru="Сандалии",
        slot="feet_armor",
        type="armor",
        defense_type="magical",
        allowed_materials=["cloths", "leathers"],
        base_power=1,
        base_durability=25,
        damage_spread=0.0,
        narrative_tags=["sandals", "light_footwear"],
        implicit_bonuses={
            "energy_regen": 0.5,
            "dodge_chance": 0.05,
        },
    ),
}
