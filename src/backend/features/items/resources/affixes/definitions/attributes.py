from ..schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)

attribute_strength = AffixCatalogEntryDTO(
    id="attribute_strength",
    group="attributes",
    technical=AffixTechnicalDTO(
        # Targets the attributes block, not modifiers — feeds derivation bridge via MODIFIER_RULES.
        modifier_id="strength_add",
        base_value=0.25,
        value_kind="flat_int",
        roll_profile=AffixRollProfileDTO(step_spread=0.10, rounding="floor_int", round_digits=0),
        min_item_tier=1,
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Strength",
        ui_template="+{value} Strength",
        narrative_tags=("powerful", "warrior", "strong"),
    ),
)

attribute_perception = AffixCatalogEntryDTO(
    id="attribute_perception",
    group="attributes",
    technical=AffixTechnicalDTO(
        modifier_id="perception_add",
        base_value=0.25,
        value_kind="flat_int",
        roll_profile=AffixRollProfileDTO(step_spread=0.10, rounding="floor_int", round_digits=0),
        min_item_tier=1,
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Perception",
        ui_template="+{value} Perception",
        narrative_tags=("perceptive", "sharp", "keen"),
    ),
)

attribute_agility = AffixCatalogEntryDTO(
    id="attribute_agility",
    group="attributes",
    technical=AffixTechnicalDTO(
        modifier_id="agility_add",
        base_value=0.25,
        value_kind="flat_int",
        roll_profile=AffixRollProfileDTO(step_spread=0.10, rounding="floor_int", round_digits=0),
        min_item_tier=1,
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Agility",
        ui_template="+{value} Agility",
        narrative_tags=("agile", "nimble", "quick"),
    ),
)

ATTRIBUTES_AFFIXES = [
    attribute_strength,
    attribute_perception,
    attribute_agility,
]
