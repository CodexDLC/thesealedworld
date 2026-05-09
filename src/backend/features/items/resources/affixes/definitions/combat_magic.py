from ..schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)

magic_damage_bonus = AffixCatalogEntryDTO(
    id="magic_damage_bonus",
    group="combat_magic",
    technical=AffixTechnicalDTO(
        modifier_id="magical_damage_bonus_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Magic Damage",
        ui_template="+{value}% Magic Damage",
        narrative_tags=("arcane", "charged", "spellbound"),
    ),
)

magic_penetration_bonus = AffixCatalogEntryDTO(
    id="magic_penetration_bonus",
    group="combat_magic",
    technical=AffixTechnicalDTO(
        modifier_id="magical_penetration_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Magic Penetration",
        ui_template="+{value}% Magic Penetration",
        narrative_tags=("piercing", "arcane", "resonant"),
    ),
)

fire_damage_bonus = AffixCatalogEntryDTO(
    id="fire_damage_bonus",
    group="combat_magic",
    technical=AffixTechnicalDTO(
        modifier_id="fire_damage_bonus_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Fire Damage",
        ui_template="+{value}% Fire Damage",
        narrative_tags=("fire", "plasma", "burning"),
    ),
)

fire_resistance_bonus = AffixCatalogEntryDTO(
    id="fire_resistance_bonus",
    group="combat_magic",
    technical=AffixTechnicalDTO(
        modifier_id="fire_resistance_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Fire Resistance",
        ui_template="+{value}% Fire Resistance",
        narrative_tags=("fireproof", "plasma", "warded"),
    ),
)

arcane_resistance_bonus = AffixCatalogEntryDTO(
    id="arcane_resistance_bonus",
    group="combat_magic",
    technical=AffixTechnicalDTO(
        modifier_id="arcane_resistance_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Arcane Resistance",
        ui_template="+{value}% Arcane Resistance",
        narrative_tags=("arcane", "warded", "resonant"),
    ),
)

COMBAT_MAGIC_AFFIXES = [
    magic_damage_bonus,
    magic_penetration_bonus,
    fire_damage_bonus,
    fire_resistance_bonus,
    arcane_resistance_bonus,
]
