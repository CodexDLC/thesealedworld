from __future__ import annotations

from typing import Any

from src.shared.enums import CoreDomain


def build_game_nav(*, state: CoreDomain | str, char_id: int) -> dict[str, dict[str, Any]]:
    current = state.value if isinstance(state, CoreDomain) else str(state)
    if current == CoreDomain.SCENARIO.value:
        return {
            "l2": None,
            "l1": None,
            "center": None,
            "r1": None,
            "r2": None,
        }

    if current == CoreDomain.EXPLORATION.value:
        return {
            "l2": _item("STATUS", "#", False, icon="person", panel="left", panel_view="status"),
            "l1": _item("QUESTS", "#", False, icon="journal", modal="quests"),
            "center": _item("EXPLORE", "#", True, icon="map"),
            "r1": _item("INVENTORY", "#", False, icon="inventory", panel="right", panel_view="inventory"),
            "r2": _item("VIEW", "#", False, icon="journal", panel="right", panel_view="context"),
        }

    center_labels = {
        CoreDomain.COMBAT.value: "COMBAT",
        CoreDomain.ARENA.value: "ARENA",
        CoreDomain.CITY_SERVICES.value: "SERVICE",
    }
    center_icons = {
        CoreDomain.COMBAT.value: "swords",
        CoreDomain.ARENA.value: "swords",
        CoreDomain.CITY_SERVICES.value: "tavern",
    }

    if current == CoreDomain.COMBAT.value:
        return {
            "l2": _item("STATUS", "#", False, icon="person", panel="left", panel_view="status"),
            "l1": _disabled_item("BUILDS", icon="bolt"),
            "center": _item("COMBAT", "#", True, icon="swords"),
            "r1": _disabled_item("INVENTORY", icon="inventory"),
            "r2": _item("VIEW", "#", False, icon="journal", panel="right", panel_view="context"),
        }

    if current == CoreDomain.ARENA.value:
        return {
            "l2": _item("STATUS", "#", False, icon="person", panel="left", panel_view="status"),
            "l1": _item("QUESTS", "#", False, icon="journal", modal="quests"),
            "center": _item("ARENA", "#", True, icon="swords"),
            "r1": _item("INVENTORY", "#", False, icon="inventory", panel="right", panel_view="inventory"),
            "r2": _item("VIEW", "#", False, icon="journal", panel="right", panel_view="context"),
        }

    if current == CoreDomain.RIFT.value:
        return {
            "l2": _item("STATUS", "#", False, icon="person", panel="left", panel_view="status"),
            "l1": _disabled_item("PARTY", icon="journal"),
            "center": _item("RIFT", "#", True, icon="map"),
            "r1": _item("INVENTORY", "#", False, icon="inventory", panel="right", panel_view="inventory"),
            "r2": _item("INFO", "#", False, icon="journal", panel="right", panel_view="context"),
        }

    if current == CoreDomain.DEATH.value:
        return {
            "l2": _item("STATUS", "#", False, icon="person", panel="left", panel_view="status"),
            "l1": _disabled_item("BUILDS", icon="bolt"),
            "center": _item("DEATH", "#", True, icon="skull"),
            "r1": _disabled_item("INVENTORY", icon="inventory"),
            "r2": _disabled_item("VIEW", icon="journal"),
        }

    if current == CoreDomain.LOOT.value:
        return {
            "l2": _item("STATUS", "#", False, icon="person", panel="left", panel_view="status"),
            "l1": _disabled_item("BUILDS", icon="bolt"),
            "center": _item("LOOT", "#", True, icon="inventory"),
            "r1": _disabled_item("INVENTORY", icon="inventory"),
            "r2": _disabled_item("VIEW", icon="journal"),
        }

    return {
        "l2": _item("STATUS", "#", False, icon="person", panel="left", panel_view="status"),
        "l1": _item("BUILDS", "#", False, icon="bolt", panel="left", panel_view="builds"),
        "center": _item(center_labels.get(current, current), "#", True, icon=center_icons.get(current, "unknown")),
        "r1": _item("INVENTORY", "#", False, icon="inventory", panel="right", panel_view="inventory"),
        "r2": _item("VIEW", "#", False, icon="journal", panel="right", panel_view="context"),
    }


def _item(
    label: str,
    url: str,
    is_active: bool,
    *,
    icon: str,
    panel: str | None = None,
    panel_view: str | None = None,
    window: str | None = None,
    modal: str | None = None,
) -> dict[str, Any]:
    return {
        "label": label,
        "url": url,
        "is_active": is_active,
        "icon": icon,
        "panel": panel,
        "panel_view": panel_view,
        "window": window,
        "modal": modal,
        "is_disabled": False,
    }


def _empty_item() -> dict[str, Any]:
    return {
        "label": "",
        "url": "#",
        "is_active": False,
        "icon": None,
        "panel": None,
        "panel_view": None,
        "window": None,
        "modal": None,
        "is_disabled": True,
    }


def _disabled_item(label: str, *, icon: str) -> dict[str, Any]:
    item = _item(label, "#", False, icon=icon)
    item["is_disabled"] = True
    return item
