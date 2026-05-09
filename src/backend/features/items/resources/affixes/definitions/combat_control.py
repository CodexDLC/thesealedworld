from ..schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)

control_chance_bonus = AffixCatalogEntryDTO(
    id="control_chance_bonus",
    group="combat_control",
    technical=AffixTechnicalDTO(
        modifier_id="control_chance_add",
        base_value=0.002,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Control Chance",
        ui_template="+{value}% Control Chance",
        narrative_tags=("controlling", "commanding", "tactical"),
    ),
)

control_resistance_bonus = AffixCatalogEntryDTO(
    id="control_resistance_bonus",
    group="combat_control",
    technical=AffixTechnicalDTO(
        modifier_id="control_resistance_add",
        base_value=0.0025,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.05, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Control Resistance",
        ui_template="+{value}% Control Resistance",
        narrative_tags=("resolute", "unbowed", "iron-willed"),
    ),
)

COMBAT_CONTROL_AFFIXES = [
    control_chance_bonus,
    control_resistance_bonus,
]
