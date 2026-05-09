from ..schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)

armor_flat = AffixCatalogEntryDTO(
    id="armor_flat",
    group="combat_defense",
    technical=AffixTechnicalDTO(
        modifier_id="armor_add",
        base_value=0.5,
        value_kind="flat_decimal",
        roll_profile=AffixRollProfileDTO(step_spread=0.15, rounding="decimal", round_digits=2),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Armor",
        ui_template="+{value} Armor",
        narrative_tags=("solid", "reinforced", "durable"),
    ),
)

evasion_bonus = AffixCatalogEntryDTO(
    id="evasion_bonus",
    group="combat_defense",
    technical=AffixTechnicalDTO(
        modifier_id="evasion_add",
        base_value=0.0025,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.05, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Evasion",
        ui_template="+{value}% Evasion",
        narrative_tags=("nimble", "agile", "quick"),
    ),
)

physical_resistance_bonus = AffixCatalogEntryDTO(
    id="physical_resistance_bonus",
    group="combat_defense",
    technical=AffixTechnicalDTO(
        modifier_id="physical_resistance_add",
        base_value=0.0025,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.05, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Physical Resistance",
        ui_template="+{value}% Physical Resistance",
        narrative_tags=("hardened", "resilient", "tough"),
    ),
)

block_bonus = AffixCatalogEntryDTO(
    id="block_bonus",
    group="combat_defense",
    technical=AffixTechnicalDTO(
        modifier_id="block_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
        required_item_tags=("shield",),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Block Chance",
        ui_template="+{value}% Block",
        narrative_tags=("guard", "stalwart", "defender"),
    ),
)

shield_guard_power_bonus = AffixCatalogEntryDTO(
    id="shield_guard_power_bonus",
    group="combat_defense",
    technical=AffixTechnicalDTO(
        modifier_id="shield_guard_power_add",
        base_value=0.5,
        value_kind="flat_decimal",
        roll_profile=AffixRollProfileDTO(step_spread=0.15, rounding="decimal", round_digits=2),
        required_item_tags=("shield",),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Shield Guard Power",
        ui_template="+{value} Shield Guard",
        narrative_tags=("guard", "absorb", "bastion"),
    ),
)

thorns_damage_bonus = AffixCatalogEntryDTO(
    id="thorns_damage_bonus",
    group="combat_defense",
    technical=AffixTechnicalDTO(
        modifier_id="thorns_damage_flat_add",
        base_value=0.25,
        value_kind="flat_decimal",
        roll_profile=AffixRollProfileDTO(step_spread=0.15, rounding="decimal", round_digits=2),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Thorns Damage",
        ui_template="+{value} Thorns",
        narrative_tags=("spiked", "reflective", "punishing"),
    ),
)

COMBAT_DEFENSE_AFFIXES = [
    armor_flat,
    evasion_bonus,
    physical_resistance_bonus,
    block_bonus,
    shield_guard_power_bonus,
    thorns_damage_bonus,
]
