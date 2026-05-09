from ..schemas import AffixBundleDTO

survival_garment_3 = AffixBundleDTO(
    id="survival_garment_3",
    size=3,
    affix_ids=("cold_resistance_bonus", "heat_resistance_bonus", "bio_resistance_bonus"),
    allowed_item_types=("garment",),
    min_item_tier=0,
    tags=("survival", "garment", "environment"),
    source_constraints=(),
)

scout_garment_3 = AffixBundleDTO(
    id="scout_garment_3",
    size=3,
    affix_ids=("travel_speed", "scouting_bonus", "evasion_bonus"),
    allowed_item_types=("garment",),
    min_item_tier=1,
    tags=("scout", "garment", "mobile"),
    source_constraints=(),
)

scout_accessory_3 = AffixBundleDTO(
    id="scout_accessory_3",
    size=3,
    affix_ids=("travel_speed", "scouting_bonus", "luck_bonus"),
    allowed_item_types=("accessory",),
    min_item_tier=1,
    tags=("scout", "accessory", "mobile"),
    source_constraints=(),
)

BUNDLES_3 = [
    survival_garment_3,
    scout_garment_3,
    scout_accessory_3,
]
