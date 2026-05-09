from ..schemas import (
    AffixCatalogEntryDTO,
    AffixDescriptiveDTO,
    AffixRollProfileDTO,
    AffixTechnicalDTO,
)

trade_bonus = AffixCatalogEntryDTO(
    id="trade_bonus",
    group="economy",
    technical=AffixTechnicalDTO(
        # Future world field — not yet in CombatModifiersDTO.
        modifier_id="trade_bonus_add",
        base_value=0.003,
        value_kind="probability",
        roll_profile=AffixRollProfileDTO(step_spread=0.08, rounding="decimal", round_digits=4),
    ),
    descriptive=AffixDescriptiveDTO(
        display_name="Trade Bonus",
        ui_template="+{value}% Trade Value",
        narrative_tags=("merchant", "shrewd", "profitable"),
    ),
)

ECONOMY_AFFIXES = [
    trade_bonus,
]
