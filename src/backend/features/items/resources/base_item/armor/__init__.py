from .heavy import HEAVY_ARMOR_DB
from .light import LIGHT_ARMOR_DB
from .medium import MEDIUM_ARMOR_DB

ARMOR_DB = {
    "heavy": HEAVY_ARMOR_DB,
    "light": LIGHT_ARMOR_DB,
    "medium": MEDIUM_ARMOR_DB,
}

__all__ = ["ARMOR_DB"]
