from __future__ import annotations

from src.backend.features.game_catalog.combat.resources import (
    get_ability_catalog_entry_by_key,
    get_ability_config,
    get_basic_exchange_entry,
    get_combat_catalog_entry_by_key,
    get_combat_item_action,
    get_combat_item_action_catalog_entry_by_key,
    get_effect_catalog_entry,
    get_effect_catalog_entry_by_key,
    get_effect_config,
    get_feint_catalog_entry_by_key,
    get_feint_config,
    get_gift_catalog_entry_by_key,
    get_gift_config,
    get_pipeline_preset,
    get_trigger_catalog_entry,
    get_trigger_catalog_entry_by_key,
    get_trigger_rule,
)


class CombatCatalogIntegrator:
    """Combat runtime access facade for game_catalog-owned combat dictionaries."""

    get_ability = staticmethod(get_ability_config)
    get_ability_catalog_entry_by_key = staticmethod(get_ability_catalog_entry_by_key)
    get_effect = staticmethod(get_effect_config)
    get_effect_catalog_entry = staticmethod(get_effect_catalog_entry)
    get_effect_catalog_entry_by_key = staticmethod(get_effect_catalog_entry_by_key)
    get_feint = staticmethod(get_feint_config)
    get_feint_catalog_entry_by_key = staticmethod(get_feint_catalog_entry_by_key)
    get_catalog_entry_by_key = staticmethod(get_combat_catalog_entry_by_key)
    get_gift = staticmethod(get_gift_config)
    get_gift_catalog_entry_by_key = staticmethod(get_gift_catalog_entry_by_key)
    get_combat_item_action = staticmethod(get_combat_item_action)
    get_combat_item_action_catalog_entry_by_key = staticmethod(get_combat_item_action_catalog_entry_by_key)
    get_trigger_rule = staticmethod(get_trigger_rule)
    get_trigger_catalog_entry = staticmethod(get_trigger_catalog_entry)
    get_trigger_catalog_entry_by_key = staticmethod(get_trigger_catalog_entry_by_key)
    get_pipeline_preset = staticmethod(get_pipeline_preset)
    get_basic_exchange = staticmethod(get_basic_exchange_entry)
