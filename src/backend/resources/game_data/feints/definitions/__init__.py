from .dirty import DIRTY_FEINTS
from .tactical import TACTICAL_FEINTS
from .weapon_moves import WEAPON_FEINTS

ALL_FEINTS_LIST = TACTICAL_FEINTS + DIRTY_FEINTS + WEAPON_FEINTS

FEINTS_DICT = {f.feint_id: f for f in ALL_FEINTS_LIST}
