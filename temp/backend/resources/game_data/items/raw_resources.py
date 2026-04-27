"""
ГЛОБАЛЬНЫЙ РЕЕСТР СЫРЬЕВЫХ РЕСУРСОВ
====================================

Этот модуль собирает все категории сырья в единый словарь RAW_RESOURCES_DB.

Подробные данные находятся внутри соответствующих модулей в папке `raw_resource/`.
"""

from typing import Any, cast

from src.backend.resources.game_data.items.schemas import ResourceDTO

from .raw_resource.bark import BARK_DB
from .raw_resource.common_supplies import COMMON_SUPPLIES_DB
from .raw_resource.currency import CURRENCY_DB
from .raw_resource.essences import ESSENCES_DB
from .raw_resource.fibers import FIBERS_DB
from .raw_resource.flowers import FLOWERS_DB
from .raw_resource.hides import HIDES_DB
from .raw_resource.ores import ORES_DB
from .raw_resource.stone import STONE_DB
from .raw_resource.woods import WOODS_DB

# Сборка единой базы данных из модулей
# Используем оператор | (Python 3.9+) для объединения словарей
RAW_RESOURCES_DB: dict[str, dict[Any, ResourceDTO]] = (
    cast(dict[str, dict[Any, ResourceDTO]], CURRENCY_DB)
    | cast(dict[str, dict[Any, ResourceDTO]], ORES_DB)
    | cast(dict[str, dict[Any, ResourceDTO]], HIDES_DB)
    | cast(dict[str, dict[Any, ResourceDTO]], WOODS_DB)
    | cast(dict[str, dict[Any, ResourceDTO]], FIBERS_DB)
    | cast(dict[str, dict[Any, ResourceDTO]], ESSENCES_DB)
    | cast(dict[str, dict[Any, ResourceDTO]], STONE_DB)
    | cast(dict[str, dict[Any, ResourceDTO]], BARK_DB)
    | cast(dict[str, dict[Any, ResourceDTO]], FLOWERS_DB)
    | cast(dict[str, dict[Any, ResourceDTO]], COMMON_SUPPLIES_DB)
)
