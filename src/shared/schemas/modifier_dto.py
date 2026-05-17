"""
Модуль содержит DTO (Data Transfer Objects) для модификаторов характеристик персонажа.
Определяет структуру боевых и небоевых модификаторов.

СИНХРОНИЗИРОВАНО С: src/shared/enums/stats_enums.py
"""

from pydantic import BaseModel, ConfigDict

# ==============================================================================
# 1. ATOMIC BLOCKS (Кирпичики)
# ==============================================================================


class VitalsDTO(BaseModel):
    """Ресурсы (HP, Energy, Stamina) и Инициатива."""

    hp: int = 0  # StatKey.HP
    hp_regen: float = 0.0  # StatKey.HP_REGEN

    en: int = 0  # StatKey.EN
    en_regen: float = 0.0  # StatKey.EN_REGEN

    stamina: int = 0  # StatKey.STAMINA
    stamina_regen: float = 0.0  # StatKey.STAMINA_REGEN

    resource_cost_reduction: float = 0.0
    initiative: float = 0.0  # StatKey.INITIATIVE


class CombatSkillsDTO(BaseModel):
    """
    Боевые навыки (Weapon, Armor, Tactical, Support).
    Список строго соответствует документации.
    """

    # Weapon Mastery
    skill_swords: float = 0.0
    skill_fencing: float = 0.0
    skill_polearms: float = 0.0
    skill_macing: float = 0.0
    skill_archery: float = 0.0
    skill_unarmed: float = 0.0

    # Tactical Styles
    skill_one_handed: float = 0.0
    skill_two_handed: float = 0.0
    skill_shield_mastery: float = 0.0
    skill_dual_wield: float = 0.0

    # Armor Skills
    skill_light_armor: float = 0.0
    skill_medium_armor: float = 0.0
    skill_heavy_armor: float = 0.0

    # Secondary Combat
    skill_parrying: float = 0.0
    skill_anatomy: float = 0.0
    skill_tactics: float = 0.0


class SecondarySkillsDTO(BaseModel):
    """Второстепенные навыки."""

    # Crafting
    skill_first_aid: float = 0.0
    skill_alchemy: float = 0.0
    skill_weapon_craft: float = 0.0
    skill_armor_craft: float = 0.0
    skill_jewelry_craft: float = 0.0
    skill_artifact_craft: float = 0.0
    skill_engineering: float = 0.0

    skill_mining: float = 0.0
    skill_herbalism: float = 0.0
    skill_skinning: float = 0.0
    skill_woodcutting: float = 0.0
    skill_hunting: float = 0.0
    skill_archaeology: float = 0.0

    # Survival
    skill_taming: float = 0.0
    skill_adaptation: float = 0.0
    skill_scouting: float = 0.0
    skill_pathfinder: float = 0.0

    skill_accounting: float = 0.0
    skill_brokerage: float = 0.0
    skill_contracts: float = 0.0
    skill_trade_relations: float = 0.0

    skill_leadership: float = 0.0
    skill_organization: float = 0.0
    skill_team_spirit: float = 0.0
    skill_egoism: float = 0.0


class MainHandStatsDTO(BaseModel):
    """
    Статы ПРАВОЙ руки (или Двуручного оружия).
    """

    main_hand_damage_base: float = 0.0
    main_hand_damage_spread: float = 0.1
    main_hand_damage_bonus: float = 0.0
    main_hand_armor_penetration_pct: float = 0.0
    main_hand_armor_ignore_chance: float = 0.0
    main_hand_accuracy: float = 0.0

    # Crit
    main_hand_crit_chance: float = 0.0
    main_hand_crit_cap: float = 0.75


class OffHandStatsDTO(BaseModel):
    """
    Статы ЛЕВОЙ руки (Второе оружие или Щит).
    """

    off_hand_damage_base: float = 0.0
    off_hand_damage_spread: float = 0.1
    off_hand_damage_bonus: float = 0.0
    off_hand_armor_penetration_pct: float = 0.0
    off_hand_armor_ignore_chance: float = 0.0
    off_hand_accuracy: float = 0.0

    # Crit
    off_hand_crit_chance: float = 0.0
    off_hand_crit_cap: float = 0.75


class ItemStatsDTO(BaseModel):
    """
    Статы БОЕВЫХ ПРЕДМЕТОВ (Гранаты, Свитки, Метательное).
    Используются, когда source_type="item".
    """

    item_damage_base: float = 0.0
    item_damage_spread: float = 0.1
    item_damage_bonus: float = 0.0
    item_armor_penetration_pct: float = 0.0
    item_armor_ignore_chance: float = 0.0
    item_accuracy: float = 0.0
    item_crit_chance: float = 0.0
    item_crit_cap: float = 0.75


class PhysicalStatsDTO(BaseModel):
    """
    Глобальные физические бонусы (работают на обе руки).
    """

    physical_damage: float = 0.0  # StatKey.PHYSICAL_DAMAGE (Base Bonus)
    physical_damage_bonus: float = 0.0  # % Bonus

    accuracy: float = 0.0  # StatKey.ACCURACY (Global)
    physical_suppression: float = 0.0  # StatKey.PHYSICAL_SUPPRESSION (Global)
    armor_penetration_pct: float = 0.0  # StatKey.ARMOR_PENETRATION_PCT (Global)
    armor_penetration_flat: float = 0.0  # StatKey.ARMOR_PENETRATION_FLAT (Global)
    armor_ignore_chance: float = 0.0  # StatKey.ARMOR_IGNORE_CHANCE (Global)

    crit_chance: float = 0.0  # StatKey.CRIT_CHANCE (Global)
    crit_power: float = 0.0  # StatKey.CRIT_POWER


class MagicalStatsDTO(BaseModel):
    """Магическая атака (База)."""

    magical_damage: float = 0.0  # StatKey.MAGICAL_DAMAGE
    magical_damage_spread: float = 0.1
    magical_damage_bonus: float = 0.0

    magical_accuracy: float = 0.0
    magical_damage_power: float = 0.0
    magical_penetration: float = 0.0  # <--- RESTORED
    spell_land_chance: float = 0.0

    # Magical Crit (Пока общий)
    magical_crit_chance: float = 0.0
    magical_crit_cap: float = 0.75


class DefensiveStatsDTO(BaseModel):
    """
    Активная защита (Avoidance).
    """

    # Dodge / Evasion
    evasion: float = 0.0  # StatKey.EVASION
    dodge_cap: float = 0.75
    anti_dodge_chance: float = 0.0

    # Parry
    parry: float = 0.0  # StatKey.PARRY
    parry_cap: float = 0.50

    # Block
    block: float = 0.0  # StatKey.BLOCK
    shield_block_cap: float = 0.75


class MitigationStatsDTO(BaseModel):
    """
    Снижение урона (Reduction).
    """

    # Resists
    physical_resistance: float = 0.0
    magic_resist: float = 0.0  # StatKey.MAGIC_RESIST
    resistance_cap: float = 0.85

    # Armor (Flat)
    armor: float = 0.0  # StatKey.ARMOR
    shield_guard_power: float = 0.0
    shield_absorb_ratio: float = 0.40
    shield_reflect_ratio: float = 0.50


class ElementalStatsDTO(BaseModel):
    """
    Стихии (8 базовых).
    """

    fire_damage_bonus: float = 0.0
    fire_resistance: float = 0.0

    water_damage_bonus: float = 0.0
    water_resistance: float = 0.0

    air_damage_bonus: float = 0.0
    air_resistance: float = 0.0

    earth_damage_bonus: float = 0.0
    earth_resistance: float = 0.0

    light_damage_bonus: float = 0.0
    light_resistance: float = 0.0

    dark_damage_bonus: float = 0.0
    dark_resistance: float = 0.0

    arcane_damage_bonus: float = 0.0
    arcane_resistance: float = 0.0

    nature_damage_bonus: float = 0.0
    nature_resistance: float = 0.0


class StatusStatsDTO(BaseModel):
    """
    Сопротивление статусам, контролю и DoT.
    """

    # Control (Mental)
    control_chance_bonus: float = 0.0  # NEW: Шанс наложить контроль
    control_resistance: float = 0.0  # Защита от контроля
    mental_resistance: float = 0.0  # NEW: Ментальная защита (страх, сон)
    debuff_avoidance: float = 0.0  # Шанс избежать любого дебаффа
    shock_resistance: float = 0.0

    # Poison
    poison_damage_bonus: float = 0.0
    poison_resistance: float = 0.0
    poison_efficiency: float = 0.0

    # Bleed
    bleed_damage_bonus: float = 0.0
    bleed_resistance: float = 0.0


class SpecialStatsDTO(BaseModel):
    """
    Спец. механики (Вампиризм, Хил, Отражение).
    """

    counter_attack_chance: float = 0.0
    counter_attack_cap: float = 0.50

    vampiric_power: float = 0.0
    vampiric_trigger_chance: float = 0.0
    vampiric_trigger_cap: float = 1.0

    healing_power: float = 0.0
    received_healing_bonus: float = 0.0

    pet_efficiency_mult: float = 1.0

    damage_mult: float = 1.0

    thorns_damage_flat: float = 0.0

    hand_size: int = 3


class EnvironmentalStatsDTO(BaseModel):
    """Защита от среды."""

    environment_cold_resistance: float = 0.0
    environment_heat_resistance: float = 0.0
    environment_gravity_resistance: float = 0.0
    environment_bio_resistance: float = 0.0


class SpeedStatsDTO(BaseModel):
    """Скоростные характеристики."""

    attack_speed: float = 0.0  # StatKey.ATTACK_SPEED
    cast_speed: float = 0.0  # StatKey.CAST_SPEED
    movement_speed: float = 0.0  # StatKey.MOVEMENT_SPEED


# ==============================================================================
# 2. COMBAT MODIFIERS (Основной DTO)
# ==============================================================================


class CombatModifiersDTO(
    VitalsDTO,
    # CombatSkillsDTO удален отсюда!
    MainHandStatsDTO,
    OffHandStatsDTO,
    ItemStatsDTO,
    PhysicalStatsDTO,
    MagicalStatsDTO,
    DefensiveStatsDTO,
    MitigationStatsDTO,
    ElementalStatsDTO,
    StatusStatsDTO,
    SpecialStatsDTO,
    EnvironmentalStatsDTO,
    SpeedStatsDTO,  # <--- NEW
):
    """
    Только боевые модификаторы (без скиллов).
    Используются в ActorStats.mods.
    """

    model_config = ConfigDict(extra="ignore")  # Изменил на ignore, чтобы не падать от лишних ключей


class CharacterWorldStatsDTO(BaseModel):
    """
    Хранилище мирных модификаторов персонажа.
    Загружается из Redis для проверок в диалогах, магазинах и мастерских.
    """

    model_config = ConfigDict(extra="ignore")

    # ==========================================================================
    # 💰 ЭКОНОМИКА И СОЦИУМ
    # ==========================================================================
    trade_discount: float = 0.0  # % скидки при торговле (0.1 = 10%).
    sell_price_bonus: float = 0.0  # % наценки при продаже предметов торговцу.
    social_bonus: float = 0.0  # Бонус к броскам харизмы/убеждения в диалогах.

    # ==========================================================================
    # 🔨 РЕМЕСЛО (Crafting)
    # ==========================================================================
    crafting_speed: float = 0.0  # % ускорения крафта.
    crafting_success_chance: float = 0.0  # Бонус к шансу успеха.
    crafting_critical_chance: float = 0.0  # Шанс создать предмет лучшего качества.
    resource_gathering_bonus: float = 0.0  # Бонус к количеству собираемых ресурсов.

    # ==========================================================================
    # 🎒 ИНВЕНТАРЬ И МИР
    # ==========================================================================
    weight_limit_bonus: float = 0.0  # Дополнительный переносимый вес.
    inventory_slots_bonus: int = 0  # Дополнительные слоты инвентаря.
    find_loot_chance: float = 0.0  # Magic Find (шанс найти редкий лут).
    skill_gain_bonus: float = 0.0  # Ускорение прокачки навыков.


class FullModifiersDTO(CombatModifiersDTO, CombatSkillsDTO, CharacterWorldStatsDTO):
    """
    Полный набор модификаторов (включая скиллы).
    Используется для сохранения/загрузки.
    """

    pass


class CharacterModifiersSaveDto(FullModifiersDTO):
    """
    Deprecated Alias.
    """

    pass
