from __future__ import annotations

from typing import Any

NON_WEAPON_FEINTS: tuple[str, ...] = (
    "true_strike",
    "power_attack",
    "defensive_strike",
    "sand_throw",
    "low_blow",
)

WEAPON_MASTERY_FEINTS: dict[str, tuple[str, ...]] = {
    "skill_swords": ("cleave", "pommel_strike"),
    "skill_fencing": ("piercing_thrust", "hamstring_cut"),
    "skill_polearms": ("piercing_thrust", "polearm_trip", "cleave"),
    "skill_macing": ("guard_breaker",),
    "skill_archery": ("aimed_shot",),
    "skill_unarmed": ("close_grapple",),
}

TACTICAL_STYLE_FEINTS: dict[str, tuple[str, ...]] = {
    "skill_shield_mastery": ("shield_bash",),
    "skill_two_handed": ("cleave",),
}


def build_known_feints(loadout: dict[str, Any], skills: dict[str, float] | None = None) -> list[str]:
    """Build the full pre-combat feint pool for an actor snapshot."""
    layout = _dict(loadout.get("layout"))
    known: list[str] = [*NON_WEAPON_FEINTS]

    for slot in ("main_hand", "off_hand"):
        skill_key = layout.get(slot)
        if isinstance(skill_key, str):
            known.extend(WEAPON_MASTERY_FEINTS.get(skill_key, ()))

    tactical_style = layout.get("tactical_style")
    if isinstance(tactical_style, str):
        known.extend(TACTICAL_STYLE_FEINTS.get(tactical_style, ()))

    known.extend(_item_feints(loadout))
    return list(dict.fromkeys(feint for feint in known if feint))


def _item_feints(loadout: dict[str, Any]) -> list[str]:
    feints: list[str] = []
    for item in _list(loadout.get("belt")):
        feints.extend(_feints_from_item(_dict(item)))
    return feints


def _feints_from_item(item: dict[str, Any]) -> list[str]:
    mechanics = _dict(item.get("mechanics") or item.get("data"))
    raw = (
        item.get("feints") or item.get("known_feints") or mechanics.get("feints") or mechanics.get("known_feints") or []
    )
    return [str(value) for value in raw] if isinstance(raw, list) else []


def _dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
