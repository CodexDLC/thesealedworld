from __future__ import annotations

from typing import Any

from src.frontend.config.settings import settings
from src.frontend.game_features.inventory.view_models.window import build_inventory_window_vm


def build_rift_context(
    rift: dict[str, Any],
    *,
    char_id: int = 0,
    status_seed: dict[str, Any] | None = None,
    inventory_window: Any | None = None,
    character_status: Any | None = None,
    debug_enabled: bool | None = None,
) -> dict[str, Any]:
    debug = settings.debug if debug_enabled is None else bool(debug_enabled)
    status_payload = status_seed or {
        "character_id": char_id,
        "name": "Rift tester",
        "symbiote_name": "SYSTEM",
        "hp": 1,
        "max_hp": 1,
        "energy": 1,
        "max_energy": 1,
        "stamina": 1,
        "max_stamina": 1,
        "avatar_url": None,
        "gear_score": 0,
    }
    inventory_payload = inventory_window or build_inventory_window_vm(status_payload)
    character_status_payload = character_status or _character_status_from_seed(status_payload)
    return {
        "char_id": char_id,
        "domain": "rift",
        "payload_type": "rift_screen",
        "rift": rift,
        "background_url": "/static/images/exploration/city/d4/52_52_runic_circle_plaza.webp",
        "chat_ws_endpoint": _chat_ws_endpoint(settings.chat_ws_url),
        "world_resonance": "RIFT_DEV_HARNESS",
        "game_state_scripts": ["/static/js/game/states/rift.js"],
        "status_seed": status_payload,
        "inventory_window": inventory_payload,
        "character_status": character_status_payload,
        "debug_enabled": debug,
        "nav": _rift_nav(),
        "meta": {
            "title": "Test Rift",
            "robots": "noindex, nofollow",
        },
    }


def build_rift_status_seed(character_status: Any | None, *, fallback_char_id: int = 0) -> dict[str, Any]:
    if character_status is None:
        return {
            "character_id": fallback_char_id,
            "name": "Rift tester" if fallback_char_id == 0 else "NO_DATA",
            "symbiote_name": "SYSTEM" if fallback_char_id == 0 else "NO_DATA",
            "hp": 0,
            "max_hp": 1,
            "energy": 0,
            "max_energy": 1,
            "stamina": 0,
            "max_stamina": 1,
            "avatar_url": None,
            "gear_score": 0,
        }

    vitals = _value(character_status, "vitals") or {}
    bio = _value(character_status, "bio") or {}
    symbiote = _value(character_status, "symbiote") or {}
    metrics = _value(character_status, "metrics") or {}
    return {
        "character_id": _value(character_status, "char_id") or fallback_char_id,
        "name": _value(bio, "name") or "NO_DATA",
        "symbiote_name": _value(symbiote, "name")
        or _value(symbiote, "symbiote_name")
        or settings.default_symbiote_name,
        "hp": _vital_current(_value(vitals, "hp")),
        "max_hp": _vital_max(_value(vitals, "hp")),
        "energy": _vital_current(_value(vitals, "energy")),
        "max_energy": _vital_max(_value(vitals, "energy")),
        "stamina": _vital_current(_value(vitals, "stamina")),
        "max_stamina": _vital_max(_value(vitals, "stamina")),
        "avatar_url": _value(bio, "avatar"),
        "gear_score": int(_value(metrics, "gear_score") or 0),
    }


def has_rift_inventory_runtime_ref(character_status: Any | None) -> bool:
    sessions = _value(character_status, "sessions")
    return isinstance(sessions, dict) and bool(sessions.get("inventory_id"))


def _chat_ws_endpoint(raw_url: str) -> str:
    base = raw_url.rstrip("/")
    if base.endswith("/ws/chat"):
        return base
    return f"{base}/ws/chat"


def _rift_nav() -> dict[str, dict[str, Any] | None]:
    return {
        "l2": {
            "label": "STATUS",
            "url": "#",
            "is_active": False,
            "icon": "person",
            "panel": "left",
            "panel_view": "status",
            "is_disabled": False,
        },
        "l1": {
            "label": "PARTY",
            "url": "#",
            "is_active": False,
            "icon": "journal",
            "panel": None,
            "panel_view": None,
            "is_disabled": True,
        },
        "center": {
            "label": "RIFT",
            "url": "#",
            "is_active": True,
            "icon": "map",
            "is_disabled": False,
        },
        "r1": {
            "label": "INVENTORY",
            "url": "#",
            "is_active": False,
            "icon": "inventory",
            "panel": "right",
            "panel_view": "inventory",
            "is_disabled": False,
        },
        "r2": {
            "label": "INFO",
            "url": "#",
            "is_active": False,
            "icon": "journal",
            "panel": "right",
            "panel_view": "context",
            "is_disabled": False,
        },
    }


def _character_status_from_seed(status_seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "char_id": status_seed.get("character_id") or 0,
        "state": "RIFT",
        "bio": {
            "name": status_seed.get("name") or "Rift tester",
            "avatar": status_seed.get("avatar_url"),
        },
        "vitals": {
            "hp": {"cur": status_seed.get("hp", 0), "max": max(int(status_seed.get("max_hp") or 1), 1)},
            "energy": {
                "cur": status_seed.get("energy", 0),
                "max": max(int(status_seed.get("max_energy") or 1), 1),
            },
            "stamina": {
                "cur": status_seed.get("stamina", 0),
                "max": max(int(status_seed.get("max_stamina") or 1), 1),
            },
        },
        "attributes": {},
        "skills": {},
        "metrics": {"gear_score": int(status_seed.get("gear_score") or 0)},
        "symbiote": {"name": status_seed.get("symbiote_name") or "SYSTEM"},
        "sessions": {},
    }


def _value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _vital_current(value: Any) -> float:
    if isinstance(value, dict):
        return float(value.get("cur", 0))
    return 0.0


def _vital_max(value: Any) -> int:
    if isinstance(value, dict):
        return int(value.get("max", 1))
    return 1
