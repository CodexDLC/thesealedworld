from ..schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)

travel_speed = AffixCatalogEntryDTO(
    id="travel_speed",
    group="world_exploration",
    technical=AffixTechnicalDTO(
        # Future world field — not yet in CombatModifiersDTO.
        modifier_id="travel_speed_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.08, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Travel Speed",
        ui_template="+{value}% Travel Speed",
        narrative_tags=("swift", "ranger", "mobile"),
    ),
)

scouting_bonus = AffixCatalogEntryDTO(
    id="scouting_bonus",
    group="world_exploration",
    technical=AffixTechnicalDTO(
        modifier_id="skill_scouting_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Scouting",
        ui_template="+{value}% Scouting",
        narrative_tags=("perceptive", "ranger", "tracker"),
    ),
)

pathfinding_bonus = AffixCatalogEntryDTO(
    id="pathfinding_bonus",
    group="world_exploration",
    technical=AffixTechnicalDTO(
        modifier_id="skill_pathfinder_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.06, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Pathfinding",
        ui_template="+{value}% Pathfinding",
        narrative_tags=("explorer", "wayfarer", "navigator"),
    ),
)

WORLD_EXPLORATION_AFFIXES = [
    travel_speed,
    scouting_bonus,
    pathfinding_bonus,
]
