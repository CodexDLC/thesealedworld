from ..schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)

hp_bonus = AffixCatalogEntryDTO(
    id="hp_bonus",
    group="combat_resource",
    technical=AffixTechnicalDTO(
        modifier_id="hp_add",
        base_value=3.0,
        value_kind="flat_int",
        roll_profile=AffixRollProfileDTO(step_spread=0.15, rounding="floor_int", round_digits=0),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Maximum HP",
        ui_template="+{value} Maximum HP",
        narrative_tags=("vitality", "endurance", "hearty"),
    ),
)

en_bonus = AffixCatalogEntryDTO(
    id="en_bonus",
    group="combat_resource",
    technical=AffixTechnicalDTO(
        modifier_id="en_add",
        base_value=2.0,
        value_kind="flat_int",
        roll_profile=AffixRollProfileDTO(step_spread=0.15, rounding="floor_int", round_digits=0),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Maximum Energy",
        ui_template="+{value} Maximum Energy",
        narrative_tags=("energetic", "focused", "sustained"),
    ),
)

hp_regen_bonus = AffixCatalogEntryDTO(
    id="hp_regen_bonus",
    group="combat_resource",
    technical=AffixTechnicalDTO(
        modifier_id="hp_regen_add",
        base_value=0.0015,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.10, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="HP Regeneration",
        ui_template="+{value}% HP Regen",
        narrative_tags=("regenerating", "resilient", "sustained"),
    ),
)

COMBAT_RESOURCE_AFFIXES = [
    hp_bonus,
    en_bonus,
    hp_regen_bonus,
]
