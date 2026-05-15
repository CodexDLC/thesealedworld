from __future__ import annotations

# Tier-indexed resource lists (index = tier 0..7)
_HIDE_BY_TIER = [
    "res_torn_pelt",
    "res_rough_hide",
    "res_thick_hide",
    "res_scaled_hide",
    "res_iron_fur",
    "res_crystal_carapace",
    "res_void_skin",
    "res_ancient_scale",
]

_PROFILE_MAP: dict[str, list[str] | str] = {
    "hide": _HIDE_BY_TIER,
    "bones": "res_animal_bones",  # tier 0, always the same
    "currency": "currency_dust",  # tier 0, always the same
}


def resolve_resource(profile: str, tier: int) -> str:
    """Map a profile name + tier to a concrete resource template_id."""
    mapping = _PROFILE_MAP.get(profile)
    if mapping is None:
        return profile  # pass-through if it's already a direct template_id
    if isinstance(mapping, str):
        return mapping
    clamped = max(0, min(tier, len(mapping) - 1))
    return mapping[clamped]
