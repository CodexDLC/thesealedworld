"""Combat AI archetype assignment for generated monster variants."""

from __future__ import annotations

from typing import Final

BALANCED_AI_ARCHETYPE: Final[str] = "balanced"

_VARIANT_AI_ARCHETYPES: Final[dict[str, str]] = {
    # Berserker: direct damage, finish pressure, low self-preservation.
    "rat_brute": "berserker",
    "rotfang": "berserker",
    "dire_wolf": "berserker",
    "winter_maw": "berserker",
    "bandit_thug": "berserker",
    "bandit_cutthroat": "berserker",
    "bandit_blackguard": "berserker",
    "bandit_warlord": "berserker",
    "goblin_cutter": "berserker",
    "scrap_king": "berserker",
    # Duelist: anti-defence pressure and technical attacks.
    "tunnel_rat": "duelist",
    "pack_rat": "duelist",
    "runner": "duelist",
    "stalker": "duelist",
    "flanker": "duelist",
    "snapper": "duelist",
    "old_fang": "duelist",
    "bandit_poacher": "duelist",
    "bandit_lookout": "duelist",
    "bandit_knife_rat": "duelist",
    "bandit_raider": "duelist",
    "bandit_billhook": "duelist",
    "goblin_sneak": "duelist",
    "goblin_spearman": "duelist",
    "goblin_skirmisher": "duelist",
    # Bulwark: survival, guard, attrition.
    "swarm_rat": "bulwark",
    "plague_rat": "bulwark",
    "brood_alpha": "bulwark",
    "pack_leader": "bulwark",
    "alpha_prime": "bulwark",
    "bandit_captain": "bulwark",
    "goblin_scrapguard": "bulwark",
    "north_stasis_sovereign": "bulwark",
    "south_entropy_sovereign": "bulwark",
    "west_gravity_sovereign": "bulwark",
    "east_evolution_sovereign": "bulwark",
    # Tactician: dispel, control, debuff, team value.
    "screecher": "tactician",
    "blight_carrier": "tactician",
    "rat_king": "tactician",
    "blood_howl": "tactician",
    "bandit_hedge_wizard": "tactician",
    "bandit_kingpin": "tactician",
    "goblin_sparkpick": "tactician",
    "goblin_tinkerer": "tactician",
    "goblin_bomber": "tactician",
    "goblin_trapmaster": "tactician",
    "goblin_chief": "tactician",
}

_FAMILY_ROLE_FALLBACKS: Final[dict[tuple[str, str], str]] = {
    ("beast", "veteran"): "duelist",
    ("beast", "boss"): "berserker",
    ("humanoid", "veteran"): "duelist",
    ("humanoid", "elite"): "tactician",
    ("humanoid", "boss"): "tactician",
    ("unknown", "boss"): "bulwark",
}


def resolve_monster_ai_archetype(
    variant_id: str | None,
    family_archetype: str | None,
    role: str | None,
) -> str:
    """Return the combat AI archetype label for a monster variant.

    Known variant ids are explicit and stable. Unknown non-empty variant ids
    stay balanced so adding a new monster does not accidentally inherit broad
    role behaviour. Family/role fallback only applies when no variant id is
    available, such as minimal fallback projections.
    """
    normalized_variant = str(variant_id or "").strip().lower()
    if normalized_variant:
        return _VARIANT_AI_ARCHETYPES.get(normalized_variant, BALANCED_AI_ARCHETYPE)

    normalized_family = str(family_archetype or "").strip().lower()
    normalized_role = str(role or "").strip().lower()
    return _FAMILY_ROLE_FALLBACKS.get((normalized_family, normalized_role), BALANCED_AI_ARCHETYPE)


__all__ = ["BALANCED_AI_ARCHETYPE", "resolve_monster_ai_archetype"]
