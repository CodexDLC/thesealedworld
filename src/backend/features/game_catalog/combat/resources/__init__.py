from typing import Any

from src.backend.features.game_catalog.combat.resources.abilities import (
    get_ability_catalog_entry,
    get_ability_catalog_entry_by_key,
    get_all_ability_catalog_entries,
    get_pipeline_preset,
)
from src.backend.features.game_catalog.combat.resources.basic_exchanges import (
    get_all_basic_exchange_entries,
    get_basic_exchange_entry,
    get_basic_exchange_entry_by_key,
)
from src.backend.features.game_catalog.combat.resources.catalog import CombatResourceCatalogService
from src.backend.features.game_catalog.combat.resources.effects import (
    get_all_effect_catalog_entries,
    get_effect_catalog_entry,
    get_effect_catalog_entry_by_key,
)
from src.backend.features.game_catalog.combat.resources.feints import (
    get_all_feint_catalog_entries,
    get_feint_catalog_entry,
    get_feint_catalog_entry_by_key,
    get_feint_render_context,
)
from src.backend.features.game_catalog.combat.resources.gifts import (
    get_all_gift_catalog_entries,
    get_gift_catalog_entry,
    get_gift_catalog_entry_by_key,
)
from src.backend.features.game_catalog.combat.resources.items import (
    get_all_combat_item_action_catalog_entries,
    get_combat_item_action_catalog_entry,
    get_combat_item_action_catalog_entry_by_key,
)
from src.backend.features.game_catalog.combat.resources.tokens import get_all_combat_tokens
from src.backend.features.game_catalog.combat.resources.triggers import (
    get_all_triggers,
    get_trigger_catalog_entry,
    get_trigger_catalog_entry_by_key,
    get_trigger_rule,
)


class GameData:
    get_gift_catalog_entry = staticmethod(get_gift_catalog_entry)
    get_gift_catalog_entry_by_key = staticmethod(get_gift_catalog_entry_by_key)
    get_all_gift_catalog_entries = staticmethod(get_all_gift_catalog_entries)
    get_all_combat_tokens = staticmethod(get_all_combat_tokens)

    get_ability_catalog_entry = staticmethod(get_ability_catalog_entry)
    get_ability_catalog_entry_by_key = staticmethod(get_ability_catalog_entry_by_key)
    get_all_ability_catalog_entries = staticmethod(get_all_ability_catalog_entries)
    get_pipeline_preset = staticmethod(get_pipeline_preset)

    get_combat_item_action_catalog_entry = staticmethod(get_combat_item_action_catalog_entry)
    get_combat_item_action_catalog_entry_by_key = staticmethod(get_combat_item_action_catalog_entry_by_key)
    get_all_combat_item_action_catalog_entries = staticmethod(get_all_combat_item_action_catalog_entries)

    get_effect_catalog_entry = staticmethod(get_effect_catalog_entry)
    get_effect_catalog_entry_by_key = staticmethod(get_effect_catalog_entry_by_key)
    get_all_effect_catalog_entries = staticmethod(get_all_effect_catalog_entries)

    get_all_triggers = staticmethod(get_all_triggers)
    get_trigger_rule = staticmethod(get_trigger_rule)
    get_trigger_catalog_entry = staticmethod(get_trigger_catalog_entry)
    get_trigger_catalog_entry_by_key = staticmethod(get_trigger_catalog_entry_by_key)

    get_feint_catalog_entry = staticmethod(get_feint_catalog_entry)
    get_feint_catalog_entry_by_key = staticmethod(get_feint_catalog_entry_by_key)
    get_all_feint_catalog_entries = staticmethod(get_all_feint_catalog_entries)
    get_feint_render_context = staticmethod(get_feint_render_context)

    get_basic_exchange = staticmethod(get_basic_exchange_entry)
    get_basic_exchange_by_key = staticmethod(get_basic_exchange_entry_by_key)
    get_all_basic_exchanges = staticmethod(get_all_basic_exchange_entries)


def get_combat_catalog_entry_by_key(catalog_key: str) -> Any | None:
    for resolver in (
        get_ability_catalog_entry_by_key,
        get_gift_catalog_entry_by_key,
        get_combat_item_action_catalog_entry_by_key,
        get_feint_catalog_entry_by_key,
        get_effect_catalog_entry_by_key,
        get_trigger_catalog_entry_by_key,
        get_basic_exchange_entry_by_key,
    ):
        entry = resolver(catalog_key)
        if entry is not None:
            return entry
    return None


def get_all_combat_catalog_entries() -> list[Any]:
    return [
        *get_all_ability_catalog_entries(),
        *get_all_gift_catalog_entries(),
        *get_all_combat_item_action_catalog_entries(),
        *get_all_feint_catalog_entries(),
        *get_all_effect_catalog_entries(),
        *get_all_triggers(),
        *get_all_basic_exchange_entries(),
    ]


__all__ = [
    "CombatResourceCatalogService",
    "GameData",
    "get_ability_catalog_entry",
    "get_ability_catalog_entry_by_key",
    "get_all_ability_catalog_entries",
    "get_all_basic_exchange_entries",
    "get_all_combat_catalog_entries",
    "get_all_combat_item_action_catalog_entries",
    "get_all_effect_catalog_entries",
    "get_effect_catalog_entry",
    "get_effect_catalog_entry_by_key",
    "get_all_feint_catalog_entries",
    "get_all_gift_catalog_entries",
    "get_all_combat_tokens",
    "get_all_triggers",
    "get_basic_exchange_entry",
    "get_basic_exchange_entry_by_key",
    "get_combat_catalog_entry_by_key",
    "get_combat_item_action_catalog_entry",
    "get_combat_item_action_catalog_entry_by_key",
    "get_feint_catalog_entry",
    "get_feint_catalog_entry_by_key",
    "get_feint_render_context",
    "get_gift_catalog_entry",
    "get_gift_catalog_entry_by_key",
    "get_pipeline_preset",
    "get_trigger_rule",
    "get_trigger_catalog_entry",
    "get_trigger_catalog_entry_by_key",
]
