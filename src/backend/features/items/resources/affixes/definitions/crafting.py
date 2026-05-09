from ..schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)

crafting_speed = AffixCatalogEntryDTO(
    id="crafting_speed",
    group="crafting",
    technical=AffixTechnicalDTO(
        # Future world field — not yet in CombatModifiersDTO.
        modifier_id="crafting_speed_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.08, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Crafting Speed",
        ui_template="+{value}% Crafting Speed",
        narrative_tags=("artisan", "skilled", "efficient"),
    ),
)

resource_find_chance = AffixCatalogEntryDTO(
    id="resource_find_chance",
    group="crafting",
    technical=AffixTechnicalDTO(
        modifier_id="resource_find_chance_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.08, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Resource Find",
        ui_template="+{value}% Resource Find",
        narrative_tags=("gatherer", "lucky", "perceptive"),
    ),
)

CRAFTING_AFFIXES = [
    crafting_speed,
    resource_find_chance,
]
