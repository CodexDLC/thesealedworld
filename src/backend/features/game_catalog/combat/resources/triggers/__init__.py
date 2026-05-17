from collections import defaultdict
from typing import Any

from loguru import logger as log

from src.backend.features.game_catalog.combat.resources.triggers.definitions.catalog import ALL_TRIGGER_CATALOG_ENTRIES
from src.backend.features.game_catalog.combat.resources.triggers.schemas import (
    TriggerCatalogEntryDTO,
    TriggerTechnicalDTO,
)

# ==========================================
# 1. REGISTRY: trigger_id -> TriggerTechnicalDTO
# ==========================================
TRIGGER_REGISTRY: dict[str, TriggerTechnicalDTO] = {}

# ==========================================
# 2. CATALOG: trigger_id -> TriggerCatalogEntryDTO
# ==========================================
TRIGGER_CATALOG_REGISTRY: dict[str, TriggerCatalogEntryDTO] = {}

# ==========================================
# 3. CATALOG BY KEY: catalog_key -> TriggerCatalogEntryDTO
# ==========================================
TRIGGER_CATALOG_BY_KEY: dict[str, TriggerCatalogEntryDTO] = {}

# ==========================================
# 4. RULES: event -> { trigger_id: {event, chance, pipeline_mutations} }
#    Consumed by CombatResolver._resolve_triggers() — preserves existing contract.
# ==========================================
TRIGGER_RULES: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

_INITIALIZED = False


def _register_triggers(entries: list[TriggerCatalogEntryDTO]) -> None:
    for entry in entries:
        t = entry.technical
        trigger_id = t.trigger_id

        if trigger_id in TRIGGER_REGISTRY:
            log.warning(f"TriggerLibrary | Duplicate trigger_id: '{trigger_id}'. Overwriting.")

        TRIGGER_REGISTRY[trigger_id] = t
        TRIGGER_CATALOG_REGISTRY[trigger_id] = entry
        TRIGGER_CATALOG_BY_KEY[entry.key] = entry

        TRIGGER_RULES[t.event][trigger_id] = {
            "event": t.event,
            "chance": t.chance,
            "pipeline_mutations": t.pipeline_mutations,
            "applied_effect_ids": t.applied_effect_ids,
            "token_grants_attacker": t.token_grants_attacker,
            "token_grants_defender": t.token_grants_defender,
            "allowed_sources": t.allowed_sources,
            "stacking_rule": t.stacking_rule,
            "display_policy": t.display_policy,
            "tags": t.tags,
        }


def _initialize_library() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    log.info("TriggerLibrary | Initializing...")
    _register_triggers(ALL_TRIGGER_CATALOG_ENTRIES)
    log.info(
        f"TriggerLibrary | Loaded {len(TRIGGER_REGISTRY)} triggers. Rules compiled for {len(TRIGGER_RULES)} events."
    )
    _INITIALIZED = True


# ==========================================
# PUBLIC API
# ==========================================


def get_trigger_technical(trigger_id: str) -> TriggerTechnicalDTO | None:
    """Technical config for resolver."""
    return TRIGGER_REGISTRY.get(trigger_id)


def get_trigger_catalog_entry(trigger_id: str) -> TriggerCatalogEntryDTO | None:
    """Full catalog entry by trigger_id."""
    return TRIGGER_CATALOG_REGISTRY.get(trigger_id)


def get_trigger_catalog_entry_by_key(catalog_key: str) -> TriggerCatalogEntryDTO | None:
    """Full catalog entry by catalog key (e.g. 'combat.trigger.weapon.heavy_crit')."""
    return TRIGGER_CATALOG_BY_KEY.get(catalog_key)


def get_trigger_rule(trigger_id: str) -> dict[str, Any] | None:
    """Resolver rule dict for trigger execution."""
    t = TRIGGER_REGISTRY.get(trigger_id)
    if t is None:
        return None
    return {
        "event": t.event,
        "chance": t.chance,
        "chance_skill_key": t.chance_skill_key,
        "chance_skill_scale": t.chance_skill_scale,
        "chance_cap": t.chance_cap,
        "pipeline_mutations": t.pipeline_mutations,
        "applied_effect_ids": t.applied_effect_ids,
        "token_grants_attacker": t.token_grants_attacker,
        "token_grants_defender": t.token_grants_defender,
        "allowed_sources": t.allowed_sources,
        "stacking_rule": t.stacking_rule,
        "display_policy": t.display_policy,
        "tags": t.tags,
    }


def get_all_triggers() -> list[TriggerCatalogEntryDTO]:
    return list(TRIGGER_CATALOG_REGISTRY.values())


# Auto-init
_initialize_library()
