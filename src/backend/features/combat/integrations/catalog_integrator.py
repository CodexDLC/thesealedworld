from __future__ import annotations

from src.backend.features.game_catalog.combat.resources import (
    get_ability_config,
    get_effect_config,
    get_feint_catalog_entry_by_key,
    get_feint_config,
    get_gift_config,
    get_pipeline_preset,
    get_trigger_rule,
    get_weapon_trigger,
)


class CombatCatalogIntegrator:
    """Combat runtime access facade for game_catalog-owned combat dictionaries."""

    get_ability = staticmethod(get_ability_config)
    get_effect = staticmethod(get_effect_config)
    get_feint = staticmethod(get_feint_config)
    get_catalog_entry_by_key = staticmethod(get_feint_catalog_entry_by_key)
    get_gift = staticmethod(get_gift_config)
    get_trigger = staticmethod(get_weapon_trigger)
    get_trigger_rule = staticmethod(get_trigger_rule)
    get_pipeline_preset = staticmethod(get_pipeline_preset)
