from __future__ import annotations

from src.backend.features.items.resources.base_item.armor import ARMOR_DB
from src.backend.features.items.resources.base_item.weapons import WEAPONS_DB

SUBCATEGORY_POOLS: dict[str, list[str]] = {}

for _subcat, _items in WEAPONS_DB.items():
    SUBCATEGORY_POOLS[_subcat] = list(_items.keys())

for _subcat, _items in ARMOR_DB.items():
    SUBCATEGORY_POOLS[f"armor_{_subcat}"] = list(_items.keys())


def get_pool(subcategory: str) -> list[str]:
    return SUBCATEGORY_POOLS.get(subcategory, [])


def merged_pool(subcategories: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for subcat in subcategories:
        for base_id in get_pool(subcat):
            if base_id not in seen:
                seen.add(base_id)
                result.append(base_id)
    return result


def validate_loot_profiles() -> None:
    from src.backend.features.loot.resources.profiles import LOOT_PROFILES  # noqa: PLC0415

    errors: list[str] = []
    for pid, profile in LOOT_PROFILES.items():
        eq = profile.equipment
        if eq is None:
            continue
        if not eq.enabled_subcategories:
            errors.append(f"Profile '{pid}': FamilyEquipmentProfile has no enabled_subcategories")
            continue
        for subcat in eq.enabled_subcategories:
            pool = SUBCATEGORY_POOLS.get(subcat)
            if pool is None:
                errors.append(f"Profile '{pid}': unknown subcategory '{subcat}'")
            elif not pool:
                errors.append(f"Profile '{pid}': subcategory '{subcat}' pool is empty")
    if errors:
        raise ValueError("Loot profile validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


validate_loot_profiles()
