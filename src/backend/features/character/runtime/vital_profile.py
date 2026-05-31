from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

PLAYER_VITAL_PROFILE_NAKED = "player:naked"
PLAYER_VITAL_PROFILE_LIGHT = "player:light"
PLAYER_VITAL_PROFILE_MEDIUM = "player:medium"
PLAYER_VITAL_PROFILE_HEAVY = "player:heavy"

_ARMOR_PROFILE_BY_CLASS = {
    "light": PLAYER_VITAL_PROFILE_LIGHT,
    "medium": PLAYER_VITAL_PROFILE_MEDIUM,
    "heavy": PLAYER_VITAL_PROFILE_HEAVY,
}


def resolve_player_vital_profile_key(items: Any) -> str:
    payload = _as_dict(items)
    layout = _as_dict(payload.get("layout"))
    equipment = _as_dict(layout.get("equipment"))
    by_id = _as_dict(payload.get("by_id"))
    chest_id = equipment.get("chest_armor")
    chest_item = _as_dict(by_id.get(str(chest_id))) if chest_id else {}
    return profile_key_from_armor_class(_armor_class(chest_item))


def resolve_player_vital_profile_key_from_equipped(equipped: Iterable[Mapping[str, Any]]) -> str:
    for item in equipped:
        payload = _as_dict(item)
        mechanics = _as_dict(payload.get("mechanics"))
        if str(payload.get("slot") or mechanics.get("slot") or "") == "chest_armor":
            return profile_key_from_armor_class(_armor_class(payload))
    return PLAYER_VITAL_PROFILE_NAKED


def profile_key_from_armor_class(armor_class: str | None) -> str:
    return _ARMOR_PROFILE_BY_CLASS.get(str(armor_class or "").strip().lower(), PLAYER_VITAL_PROFILE_NAKED)


def _armor_class(item: Mapping[str, Any]) -> str | None:
    mechanics = _as_dict(item.get("mechanics"))
    metadata = _as_dict(item.get("metadata") or mechanics.get("metadata"))
    raw = item.get("armor_class") or mechanics.get("armor_class") or metadata.get("armor_class")
    return str(raw).strip().lower() if raw else None


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "PLAYER_VITAL_PROFILE_HEAVY",
    "PLAYER_VITAL_PROFILE_LIGHT",
    "PLAYER_VITAL_PROFILE_MEDIUM",
    "PLAYER_VITAL_PROFILE_NAKED",
    "profile_key_from_armor_class",
    "resolve_player_vital_profile_key",
    "resolve_player_vital_profile_key_from_equipped",
]
