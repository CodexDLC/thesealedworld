import sys

from src.studio.features.cabinet.modules.combat_ai_testing import cabinet as _cabinet

sys.modules[__name__] = _cabinet
