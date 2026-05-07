from src.backend.features.game_catalog.combat.resources.abilities import (
    get_ability_config,
    get_all_abilities,
    get_pipeline_preset,
)
from src.backend.features.game_catalog.combat.resources.catalog import CombatResourceCatalogService
from src.backend.features.game_catalog.combat.resources.effects import get_all_effects, get_effect_config
from src.backend.features.game_catalog.combat.resources.feints import (
    get_all_feint_catalog_entries,
    get_all_feints,
    get_feint_catalog_entry,
    get_feint_catalog_entry_by_key,
    get_feint_config,
)
from src.backend.features.game_catalog.combat.resources.gifts import get_all_gifts, get_gift_config
from src.backend.features.game_catalog.combat.resources.tokens import get_all_combat_tokens
from src.backend.features.game_catalog.combat.resources.triggers import (
    get_all_triggers,
    get_trigger_rule,
    get_weapon_trigger,
)


class GameData:
    get_gift = staticmethod(get_gift_config)
    get_all_gifts = staticmethod(get_all_gifts)
    get_all_combat_tokens = staticmethod(get_all_combat_tokens)

    get_ability = staticmethod(get_ability_config)
    get_all_abilities = staticmethod(get_all_abilities)
    get_pipeline_preset = staticmethod(get_pipeline_preset)

    get_effect = staticmethod(get_effect_config)
    get_all_effects = staticmethod(get_all_effects)

    get_trigger = staticmethod(get_weapon_trigger)
    get_all_triggers = staticmethod(get_all_triggers)
    get_trigger_rule = staticmethod(get_trigger_rule)

    get_feint = staticmethod(get_feint_config)
    get_all_feints = staticmethod(get_all_feints)
    get_feint_catalog_entry = staticmethod(get_feint_catalog_entry)
    get_feint_catalog_entry_by_key = staticmethod(get_feint_catalog_entry_by_key)
    get_all_feint_catalog_entries = staticmethod(get_all_feint_catalog_entries)


__all__ = [
    "CombatResourceCatalogService",
    "GameData",
    "get_ability_config",
    "get_all_abilities",
    "get_all_effects",
    "get_all_feints",
    "get_all_feint_catalog_entries",
    "get_all_gifts",
    "get_all_combat_tokens",
    "get_all_triggers",
    "get_effect_config",
    "get_feint_config",
    "get_feint_catalog_entry",
    "get_feint_catalog_entry_by_key",
    "get_gift_config",
    "get_pipeline_preset",
    "get_trigger_rule",
    "get_weapon_trigger",
]
