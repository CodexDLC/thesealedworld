"""
ГЛОБАЛЬНЫЙ РЕЕСТР БАЗОВЫХ ПРЕДМЕТОВ
===================================

Этот модуль собирает все категории предметов ("болванок") в единый словарь BASES_DB.

Подробные руководства по заполнению находятся внутри соответствующих модулей:
- Оружие:       apps/game_core/resources/game_data/items/base_item/weapons.py
- Броня:        apps/game_core/resources/game_data/items/base_item/armor.py
- Одежда:       apps/game_core/resources/game_data/items/base_item/garment.py
- Аксессуары:   apps/game_core/resources/game_data/items/base_item/accessories.py
"""

from typing import Any, cast

from src.backend.resources.game_data.items.schemas import BaseItemDTO

from .base_item.accessories import ACCESSORIES_DB
from .base_item.armor import ARMOR_DB
from .base_item.garment import GARMENT_DB
from .base_item.weapons import WEAPONS_DB

# --- Flattening Nested DBs ---
# Некоторые базы (Armor, Garment, Accessory) разделены на подкатегории.
# Для глобального реестра мы их объединяем в плоские словари.

# 1. Armor
_flat_armor: dict[str, BaseItemDTO | dict[str, Any]] = {}
for _subcat, items in ARMOR_DB.items():
    if isinstance(items, dict):
        _flat_armor.update(items)

# 2. Garment
_flat_garment: dict[str, BaseItemDTO | dict[str, Any]] = {}
for _subcat, items in GARMENT_DB.items():
    if isinstance(items, dict):
        _flat_garment.update(items)

# 3. Accessories
_flat_accessories: dict[str, BaseItemDTO | dict[str, Any]] = {}
for _subcat, items in ACCESSORIES_DB.items():
    if isinstance(items, dict):
        _flat_accessories.update(items)

# Сборка единой базы данных из модулей
# Структура: { "category_name": { "item_id": BaseItemDTO | dict } }
BASES_DB: dict[str, dict[str, BaseItemDTO | dict[str, Any]]] = {
    "weapon": cast(dict[str, BaseItemDTO | dict[str, Any]], WEAPONS_DB),
    "armor": _flat_armor,
    "garment": _flat_garment,
    "accessory": _flat_accessories,
}
