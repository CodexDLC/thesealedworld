# Affix pool constraint tables.
#
# Each table maps a grouping key to the list of allowed single-affix ids.
# The generation pipeline intersects these constraints at roll time:
#
#   allowed_pool = (
#       AFFIX_POOLS_BY_ITEM_TYPE[item_type]
#       ∩ AFFIX_POOLS_BY_SLOT.get(slot, <all>)
#       ∩ union(AFFIX_POOLS_BY_TAG[t] for t in item_tags if t in AFFIX_POOLS_BY_TAG)
#       filtered by affix.technical.min_item_tier <= item_tier
#       filtered by affix.technical.required_item_tags ⊆ item_tags
#   )
#
# World/non-combat affixes appear in garment, belt, and accessory pools only.
# mult-operation affixes should be kept rare; prefer add for stacking stats.

AFFIX_POOLS_BY_ITEM_TYPE: dict[str, list[str]] = {
    "weapon": [
        "weapon_accuracy",
        "armor_penetration_pct_bonus",
        "crit_chance",
        "off_hand_accuracy",
        "control_chance_bonus",
    ],
    "shield": [
        "shield_guard_power_bonus",
        "physical_resistance_bonus",
        "evasion_bonus",
        "control_resistance_bonus",
        "hp_bonus",
    ],
    "armor": [
        "armor_flat",
        "physical_resistance_bonus",
        "thorns_damage_bonus",
        "evasion_bonus",
        "control_resistance_bonus",
        "hp_bonus",
        "hp_regen_bonus",
        "cold_resistance_bonus",
        "heat_resistance_bonus",
        "bio_resistance_bonus",
    ],
    "garment": [
        "evasion_bonus",
        "cold_resistance_bonus",
        "heat_resistance_bonus",
        "bio_resistance_bonus",
        "travel_speed",
        "scouting_bonus",
        "pathfinding_bonus",
        "hp_regen_bonus",
    ],
    "accessory": [
        "attribute_strength",
        "attribute_perception",
        "attribute_agility",
        "crit_chance",
        "evasion_bonus",
        "hp_bonus",
        "en_bonus",
        "luck_bonus",
        "travel_speed",
        "scouting_bonus",
        "trade_bonus",
    ],
    "belt": [
        "hp_bonus",
        "en_bonus",
        "travel_speed",
        "pathfinding_bonus",
        "resource_find_chance",
        "crafting_speed",
        "luck_bonus",
    ],
}

AFFIX_POOLS_BY_SLOT: dict[str, list[str]] = {
    "main_hand": [
        "weapon_accuracy",
        "armor_penetration_pct_bonus",
        "crit_chance",
        "control_chance_bonus",
    ],
    "off_hand": [
        "shield_guard_power_bonus",
        "off_hand_accuracy",
        "evasion_bonus",
        "physical_resistance_bonus",
        "control_resistance_bonus",
    ],
    "head_armor": [
        "armor_flat",
        "physical_resistance_bonus",
        "control_resistance_bonus",
        "hp_bonus",
    ],
    "chest_armor": [
        "armor_flat",
        "physical_resistance_bonus",
        "thorns_damage_bonus",
        "evasion_bonus",
        "hp_bonus",
        "hp_regen_bonus",
        "cold_resistance_bonus",
        "heat_resistance_bonus",
    ],
    "arms_armor": [
        "armor_flat",
        "physical_resistance_bonus",
        "control_resistance_bonus",
        "hp_bonus",
    ],
    "legs_armor": [
        "armor_flat",
        "physical_resistance_bonus",
        "evasion_bonus",
        "hp_bonus",
    ],
    "feetwear": [
        "evasion_bonus",
        "travel_speed",
        "pathfinding_bonus",
        "cold_resistance_bonus",
    ],
    "chest_garment": [
        "evasion_bonus",
        "cold_resistance_bonus",
        "heat_resistance_bonus",
        "bio_resistance_bonus",
        "hp_regen_bonus",
    ],
    "legs_garment": [
        "evasion_bonus",
        "cold_resistance_bonus",
        "heat_resistance_bonus",
        "travel_speed",
    ],
    "outer_garment": [
        "cold_resistance_bonus",
        "heat_resistance_bonus",
        "bio_resistance_bonus",
        "travel_speed",
        "scouting_bonus",
    ],
    "gloves_garment": [
        "crafting_speed",
        "resource_find_chance",
        "evasion_bonus",
    ],
    "ring_1": [
        "attribute_strength",
        "attribute_perception",
        "attribute_agility",
        "crit_chance",
        "evasion_bonus",
        "luck_bonus",
        "hp_bonus",
    ],
    "ring_2": [
        "attribute_strength",
        "attribute_perception",
        "attribute_agility",
        "crit_chance",
        "evasion_bonus",
        "luck_bonus",
        "hp_bonus",
    ],
    "amulet": [
        "attribute_strength",
        "attribute_perception",
        "attribute_agility",
        "hp_bonus",
        "en_bonus",
        "luck_bonus",
    ],
    "earring": [
        "attribute_perception",
        "attribute_agility",
        "crit_chance",
        "luck_bonus",
        "scouting_bonus",
    ],
    "belt_accessory": [
        "hp_bonus",
        "en_bonus",
        "resource_find_chance",
        "crafting_speed",
        "travel_speed",
    ],
}

# Tag-based pool bias. Used for two-handed weapons, archery, magic-type items, etc.
# These narrow or expand the type pool based on extra item tags.
AFFIX_POOLS_BY_TAG: dict[str, list[str]] = {
    "two_handed": [
        "weapon_accuracy",
        "armor_penetration_pct_bonus",
        "crit_chance",
        "hp_bonus",
    ],
    "archery": [
        "weapon_accuracy",
        "crit_chance",
        "armor_penetration_pct_bonus",
        "scouting_bonus",
    ],
    "fencing": [
        "weapon_accuracy",
        "crit_chance",
        "armor_penetration_pct_bonus",
        "control_chance_bonus",
        "off_hand_accuracy",
        "evasion_bonus",
    ],
    "dagger": [
        "weapon_accuracy",
        "crit_chance",
        "armor_penetration_pct_bonus",
        "off_hand_accuracy",
        "evasion_bonus",
    ],
    "sword": [
        "weapon_accuracy",
        "crit_chance",
        "armor_penetration_pct_bonus",
        "control_chance_bonus",
    ],
    "macing": [
        "armor_penetration_pct_bonus",
        "crit_chance",
        "control_chance_bonus",
    ],
    "polearm": [
        "weapon_accuracy",
        "armor_penetration_pct_bonus",
        "control_chance_bonus",
    ],
    "magic": [
        "en_bonus",
        "hp_regen_bonus",
        "control_chance_bonus",
        "crit_chance",
    ],
    "heavy": [
        "armor_flat",
        "physical_resistance_bonus",
        "thorns_damage_bonus",
        "hp_bonus",
        "control_resistance_bonus",
    ],
    "medium": [
        "armor_flat",
        "physical_resistance_bonus",
        "evasion_bonus",
        "control_resistance_bonus",
        "hp_regen_bonus",
    ],
    "light": [
        "evasion_bonus",
        "travel_speed",
        "scouting_bonus",
        "hp_regen_bonus",
        "cold_resistance_bonus",
        "heat_resistance_bonus",
    ],
    "heavy_armor": [
        "armor_flat",
        "physical_resistance_bonus",
        "thorns_damage_bonus",
        "hp_bonus",
        "control_resistance_bonus",
    ],
    "light_armor": [
        "evasion_bonus",
        "travel_speed",
        "scouting_bonus",
        "hp_regen_bonus",
    ],
    "shield": [
        "shield_guard_power_bonus",
        "physical_resistance_bonus",
        "control_resistance_bonus",
    ],
}
