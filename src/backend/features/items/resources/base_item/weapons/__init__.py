from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .swords import SWORDS_DB

# Legacy temp tree had both base_item/weapons.py and base_item/weapons/.
# Keep the full file as the authoritative source until the weapon categories
# are split into separate resource modules.
_legacy_file = Path(__file__).resolve().parents[1] / "weapons.py"
_legacy_weapons: dict[str, Any] = {}
if _legacy_file.exists():
    spec = importlib.util.spec_from_file_location("items_legacy_weapons", _legacy_file)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _legacy_weapons = getattr(module, "WEAPONS_DB", {})

WEAPONS_DB = _legacy_weapons or SWORDS_DB

__all__ = ["WEAPONS_DB"]
