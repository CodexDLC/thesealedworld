from .archery import ARCHERY_DB
from .fencing import FENCING_DB
from .macing import MACING_DB
from .offhand import OFFHAND_DB
from .polearms import POLEARMS_DB
from .swords import SWORDS_DB

WEAPONS_DB = {
    "swords": SWORDS_DB,
    "fencing": FENCING_DB,
    "polearms": POLEARMS_DB,
    "macing": MACING_DB,
    "archery": ARCHERY_DB,
    "offhand": OFFHAND_DB,
}

__all__ = ["WEAPONS_DB"]
