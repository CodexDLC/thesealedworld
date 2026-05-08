from src.backend.features.game_catalog.combat.resources.triggers.definitions.rules.on_accuracy import (
    ON_ACCURACY_CATALOG,
)
from src.backend.features.game_catalog.combat.resources.triggers.definitions.rules.on_block import ON_BLOCK_CATALOG
from src.backend.features.game_catalog.combat.resources.triggers.definitions.rules.on_control import ON_CONTROL_CATALOG
from src.backend.features.game_catalog.combat.resources.triggers.definitions.rules.on_crit import ON_CRIT_CATALOG
from src.backend.features.game_catalog.combat.resources.triggers.definitions.rules.on_damage import ON_DAMAGE_CATALOG
from src.backend.features.game_catalog.combat.resources.triggers.definitions.rules.on_dodge import ON_DODGE_CATALOG
from src.backend.features.game_catalog.combat.resources.triggers.definitions.rules.on_parry import ON_PARRY_CATALOG
from src.backend.features.game_catalog.combat.resources.triggers.definitions.rules.styles import STYLE_CATALOG

ALL_TRIGGER_CATALOG_ENTRIES = (
    ON_ACCURACY_CATALOG
    + ON_CRIT_CATALOG
    + ON_DODGE_CATALOG
    + ON_PARRY_CATALOG
    + ON_BLOCK_CATALOG
    + ON_CONTROL_CATALOG
    + ON_DAMAGE_CATALOG
    + STYLE_CATALOG
)
