from ..schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)

cold_resistance_bonus = AffixCatalogEntryDTO(
    id="cold_resistance_bonus",
    group="world_survival",
    technical=AffixTechnicalDTO(
        modifier_id="environment_cold_resistance_add",
        base_value=0.004,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Cold Resistance",
        ui_template="+{value}% Cold Resistance",
        narrative_tags=("insulated", "hardy", "northern"),
    ),
)

heat_resistance_bonus = AffixCatalogEntryDTO(
    id="heat_resistance_bonus",
    group="world_survival",
    technical=AffixTechnicalDTO(
        modifier_id="environment_heat_resistance_add",
        base_value=0.004,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Heat Resistance",
        ui_template="+{value}% Heat Resistance",
        narrative_tags=("fireproof", "desert", "heat-adapted"),
    ),
)

bio_resistance_bonus = AffixCatalogEntryDTO(
    id="bio_resistance_bonus",
    group="world_survival",
    technical=AffixTechnicalDTO(
        modifier_id="environment_bio_resistance_add",
        base_value=0.004,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Bio Resistance",
        ui_template="+{value}% Bio Resistance",
        narrative_tags=("immune", "purified", "resilient"),
    ),
)

WORLD_SURVIVAL_AFFIXES = [
    cold_resistance_bonus,
    heat_resistance_bonus,
    bio_resistance_bonus,
]
