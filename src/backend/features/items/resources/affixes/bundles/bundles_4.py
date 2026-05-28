from ..schemas import AffixBundleDTO

duelist_weapon_4 = AffixBundleDTO(
    id="duelist_weapon_4",
    size=4,
    affix_ids=("weapon_accuracy", "armor_penetration_pct_bonus", "crit_chance", "control_chance_bonus"),
    allowed_item_types=("weapon",),
    min_item_tier=2,
    tags=("duelist", "weapon", "precision", "finesse"),
    source_constraints=(),
)

duelist_accessory_4 = AffixBundleDTO(
    id="duelist_accessory_4",
    size=4,
    affix_ids=("attribute_agility", "attribute_perception", "crit_chance", "evasion_bonus"),
    allowed_item_types=("accessory",),
    min_item_tier=2,
    tags=("duelist", "accessory", "precision", "finesse"),
    source_constraints=(),
)

bulwark_shield_4 = AffixBundleDTO(
    id="bulwark_shield_4",
    size=4,
    affix_ids=("block_bonus", "shield_guard_power_bonus", "physical_resistance_bonus", "control_resistance_bonus"),
    allowed_item_types=("shield",),
    min_item_tier=1,
    tags=("bulwark", "shield", "tank", "defender"),
    source_constraints=(),
)

bulwark_armor_4 = AffixBundleDTO(
    id="bulwark_armor_4",
    size=4,
    affix_ids=("armor_flat", "physical_resistance_bonus", "thorns_damage_bonus", "hp_bonus"),
    allowed_item_types=("armor",),
    min_item_tier=1,
    tags=("bulwark", "armor", "tank", "defender"),
    source_constraints=(),
)

BUNDLES_4 = [
    duelist_weapon_4,
    duelist_accessory_4,
    bulwark_shield_4,
    bulwark_armor_4,
]
