"""
DTOs for character combat and world modifiers.

Ported from the legacy modifier DTO contract. Combat keeps these values as
runtime-calculated actor modifiers; world/exploration should normally derive
its own checks from skills and local rules instead of persisting this full set.
"""

from pydantic import BaseModel, ConfigDict


class VitalsDTO(BaseModel):
    """Resources and initiative."""

    hp: int = 0
    hp_regen: float = 0.0

    en: int = 0
    en_regen: float = 0.0

    stamina: int = 0
    stamina_regen: float = 0.0

    resource_cost_reduction: float = 0.0
    initiative: float = 0.0


class CombatSkillsDTO(BaseModel):
    """Combat skill values used by combat math."""

    skill_swords: float = 0.0
    skill_fencing: float = 0.0
    skill_polearms: float = 0.0
    skill_macing: float = 0.0
    skill_archery: float = 0.0
    skill_unarmed: float = 0.0

    skill_ranged_combat: float = 0.0
    skill_two_handed: float = 0.0
    skill_shield_mastery: float = 0.0
    skill_dual_wield: float = 0.0

    skill_light_armor: float = 0.0
    skill_medium_armor: float = 0.0
    skill_heavy_armor: float = 0.0

    skill_parrying: float = 0.0
    skill_anatomy: float = 0.0
    skill_tactics: float = 0.0


class SecondarySkillsDTO(BaseModel):
    """Secondary non-combat skill values kept for legacy compatibility."""

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
    """Main-hand or two-handed weapon modifiers."""

    main_hand_damage_base: float = 0.0
    main_hand_damage_spread: float = 0.1
    main_hand_damage_bonus: float = 0.0
    main_hand_weapon_power: float = 0.0
    main_hand_stat_damage_raw: float = 0.0
    main_hand_stat_damage_effective: float = 0.0
    main_hand_mastery_factor: float = 0.0
    main_hand_damage_spread_raw: float = 0.0
    main_hand_armor_penetration_pct: float = 0.0
    main_hand_armor_ignore_chance: float = 0.0
    main_hand_accuracy: float = 0.0
    main_hand_crit_chance: float = 0.0
    main_hand_crit_cap: float = 0.75


class OffHandStatsDTO(BaseModel):
    """Off-hand weapon or shield modifiers."""

    off_hand_damage_base: float = 0.0
    off_hand_damage_spread: float = 0.1
    off_hand_damage_bonus: float = 0.0
    off_hand_weapon_power: float = 0.0
    off_hand_stat_damage_raw: float = 0.0
    off_hand_stat_damage_effective: float = 0.0
    off_hand_mastery_factor: float = 0.0
    off_hand_damage_spread_raw: float = 0.0
    off_hand_armor_penetration_pct: float = 0.0
    off_hand_armor_ignore_chance: float = 0.0
    off_hand_accuracy: float = 0.0
    off_hand_crit_chance: float = 0.0
    off_hand_crit_cap: float = 0.75


class ItemStatsDTO(BaseModel):
    """Combat consumable or throwable item modifiers."""

    item_damage_base: float = 0.0
    item_damage_spread: float = 0.1
    item_damage_bonus: float = 0.0
    item_armor_penetration_pct: float = 0.0
    item_armor_ignore_chance: float = 0.0
    item_accuracy: float = 0.0
    item_crit_chance: float = 0.0
    item_crit_cap: float = 0.75


class PhysicalStatsDTO(BaseModel):
    """Global physical attack modifiers."""

    physical_damage: float = 0.0
    physical_strength_power: float = 0.0
    physical_agility_power: float = 0.0
    physical_endurance_power: float = 0.0
    physical_damage_bonus: float = 0.0
    accuracy: float = 0.0
    physical_suppression: float = 0.0
    armor_penetration_pct: float = 0.0
    armor_penetration_flat: float = 0.0
    armor_ignore_chance: float = 0.0
    crit_chance: float = 0.0
    crit_power: float = 0.0


class MagicalStatsDTO(BaseModel):
    """Magical attack modifiers."""

    magical_damage: float = 0.0
    magical_damage_spread: float = 0.1
    magical_damage_bonus: float = 0.0
    magical_accuracy: float = 0.0
    magical_damage_power: float = 0.0
    magical_penetration: float = 0.0
    spell_land_chance: float = 0.0
    magical_crit_chance: float = 0.0
    magical_crit_cap: float = 0.75


class DefensiveStatsDTO(BaseModel):
    """Active avoidance modifiers."""

    evasion: float = 0.0
    dodge_cap: float = 0.75
    anti_dodge_chance: float = 0.0

    parry: float = 0.0
    parry_cap: float = 0.50

    block: float = 0.0
    shield_block_cap: float = 0.75


class MitigationStatsDTO(BaseModel):
    """Damage reduction modifiers."""

    physical_resistance: float = 0.0
    magic_resist: float = 0.0
    resistance_cap: float = 0.85
    armor: float = 0.0
    shield_guard_power: float = 0.0
    shield_absorb_ratio: float = 0.40
    shield_reflect_ratio: float = 0.50


class ElementalStatsDTO(BaseModel):
    """Elemental damage and resistance modifiers."""

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
    """Control, debuff, poison, and bleed modifiers."""

    control_chance_bonus: float = 0.0
    control_resistance: float = 0.0
    mental_resistance: float = 0.0
    debuff_avoidance: float = 0.0
    shock_resistance: float = 0.0

    poison_damage_bonus: float = 0.0
    poison_resistance: float = 0.0
    poison_efficiency: float = 0.0

    bleed_damage_bonus: float = 0.0
    bleed_resistance: float = 0.0


class SpecialStatsDTO(BaseModel):
    """Special combat mechanics modifiers."""

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
    """Environmental resistance modifiers."""

    environment_cold_resistance: float = 0.0
    environment_heat_resistance: float = 0.0
    environment_gravity_resistance: float = 0.0
    environment_bio_resistance: float = 0.0


COMBAT_MODIFIER_BLOCKS: tuple[type[BaseModel], ...] = (
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
)


class CombatModifiersDTO(
    VitalsDTO,
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
):
    """Combat-only modifiers used by actor combat stats."""

    model_config = ConfigDict(extra="ignore")


class CharacterWorldStatsDTO(BaseModel):
    """Non-combat character modifiers kept for legacy compatibility."""

    model_config = ConfigDict(extra="ignore")

    trade_discount: float = 0.0
    sell_price_bonus: float = 0.0
    social_bonus: float = 0.0

    crafting_speed: float = 0.0
    crafting_success_chance: float = 0.0
    crafting_critical_chance: float = 0.0
    resource_gathering_bonus: float = 0.0

    weight_limit_bonus: float = 0.0
    inventory_slots_bonus: int = 0
    find_loot_chance: float = 0.0
    skill_gain_bonus: float = 0.0


class FullModifiersDTO(CombatModifiersDTO, CombatSkillsDTO, CharacterWorldStatsDTO):
    """Full modifier set including skills and legacy world stats."""


class CharacterModifiersSaveDTO(FullModifiersDTO):
    """Deprecated legacy save alias."""


CharacterModifiersSaveDto = CharacterModifiersSaveDTO
