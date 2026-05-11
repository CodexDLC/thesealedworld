from typing import Any

from .bases import BASES_DB
from .materials import CRAFTING_MATERIALS_DB
from .raw_resources import RAW_RESOURCES_DB

ITEM_REGISTRY: dict[str, dict[str, Any]] = {}


def _register_all_items():
    for cat, mat_tiers in CRAFTING_MATERIALS_DB.items():
        for _tier, mat_data in mat_tiers.items():
            _add_to_registry(mat_data, meta_type="material", category=cat)

    for cat, res_data in RAW_RESOURCES_DB.items():
        if cat == "supplies":
            for _id, data in res_data.items():
                _add_to_registry(data, meta_type="resource", category=cat)
        else:
            for _tier, data in res_data.items():
                _add_to_registry(data, meta_type="resource", category=cat)

    for cat, base_group in BASES_DB.items():
        for _item_id, base_data in base_group.items():
            _add_to_registry(base_data, meta_type="base", category=cat)


def _add_to_registry(data: Any, meta_type: str, category: str):
    if hasattr(data, "model_dump"):
        entry = data.model_dump()
    elif hasattr(data, "dict"):
        entry = data.dict()
    elif isinstance(data, dict):
        entry = dict(data)
    else:
        print(f"[WARNING] Unknown data type in registry: {type(data)}")
        return

    item_id = entry.get("id")
    if not item_id:
        return

    if item_id in ITEM_REGISTRY:
        print(f"[WARNING] Item Registry duplicate ID detected: {item_id}")
        return

    entry["_meta_type"] = meta_type
    entry["_meta_category"] = category
    ITEM_REGISTRY[str(item_id)] = entry


_register_all_items()


def get_base_by_id(base_id: str) -> dict[str, Any] | None:
    item = ITEM_REGISTRY.get(base_id)
    if item and item.get("_meta_type") == "base":
        return item
    return None
