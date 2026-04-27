"""
ГЛОБАЛЬНЫЙ РЕЕСТР МАТЕРИАЛОВ
============================

Этот модуль собирает все категории обработанных материалов и деталей в единый словарь CRAFTING_MATERIALS_DB.

Подробные данные находятся внутри соответствующих модулей в папке `material/`.
"""

from typing import cast

from src.backend.resources.game_data.items.schemas import MaterialDTO

from .material.cloths import CLOTHS_DB
from .material.ingots import INGOTS_DB
from .material.leathers import LEATHERS_DB
from .material.parts import PARTS_DB
from .material.woods import WOODS_DB

# Сборка единой базы данных из модулей
CRAFTING_MATERIALS_DB: dict[str, dict[int, MaterialDTO]] = (
    cast(dict[str, dict[int, MaterialDTO]], INGOTS_DB)
    | cast(dict[str, dict[int, MaterialDTO]], LEATHERS_DB)
    | cast(dict[str, dict[int, MaterialDTO]], CLOTHS_DB)
    | cast(dict[str, dict[int, MaterialDTO]], WOODS_DB)
    | cast(dict[str, dict[int, MaterialDTO]], PARTS_DB)
)
