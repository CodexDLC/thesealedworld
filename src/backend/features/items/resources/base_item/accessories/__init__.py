from .belts import BELTS_DB
from .jewelry import JEWELRY_DB
from .quivers import QUIVERS_DB

ACCESSORIES_DB = {
    "belts": BELTS_DB,
    "jewelry": JEWELRY_DB,
    "quivers": QUIVERS_DB,
}

__all__ = ["ACCESSORIES_DB"]
