from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.integrations import CombatCatalogIntegrator

if TYPE_CHECKING:
    from src.backend.features.combat.dto import ActiveEffectDTO


def effect_exclusive_channels(effect_id: str) -> frozenset[str]:
    """Return occupied prep channels for an effect.

    Catalogs may declare channels explicitly. When they do not, preparation
    effects get a conservative derived channel from their reaction outcome and
    primary behavior tags/mutations.
    """

    entry = CombatCatalogIntegrator.get_effect_catalog_entry(effect_id)
    technical = getattr(entry, "technical", None) if entry is not None else None
    if technical is None:
        return frozenset()

    explicit_many = getattr(technical, "exclusive_channels", None)
    if explicit_many:
        return frozenset(str(channel) for channel in explicit_many if channel)

    explicit_one = getattr(technical, "exclusive_channel", None)
    if explicit_one:
        return frozenset({str(explicit_one)})

    return _derive_exclusive_channels(technical)


def active_effect_exclusive_channels(effects: Iterable[ActiveEffectDTO]) -> frozenset[str]:
    channels: set[str] = set()
    for effect in effects:
        channels.update(effect_exclusive_channels(effect.effect_id))
    return frozenset(channels)


def active_effect_ids_exclusive_channels(effect_ids: Iterable[str]) -> frozenset[str]:
    channels: set[str] = set()
    for effect_id in effect_ids:
        channels.update(effect_exclusive_channels(str(effect_id)))
    return frozenset(channels)


def feint_preparation_exclusive_channels(feint_entry: Any) -> frozenset[str]:
    technical = getattr(feint_entry, "technical", None)
    prep_effects = getattr(technical, "preparation_effects", None) if technical is not None else None
    channels: set[str] = set()
    for prep in prep_effects or []:
        effect_id = prep.get("id") if isinstance(prep, dict) else getattr(prep, "id", None)
        if effect_id:
            channels.update(effect_exclusive_channels(str(effect_id)))
    return frozenset(channels)


def would_conflict_with_active_effects(effect_id: str, active_effects: Iterable[ActiveEffectDTO]) -> bool:
    incoming = effect_exclusive_channels(effect_id)
    if not incoming:
        return False
    return bool(incoming & active_effect_exclusive_channels(active_effects))


def _derive_exclusive_channels(technical: Any) -> frozenset[str]:
    tags = {str(tag) for tag in getattr(technical, "tags", []) or []}
    if "preparation" not in tags:
        return frozenset()

    outcomes = {str(outcome) for outcome in getattr(technical, "react_on_outcomes", []) or []}
    mutations = {
        str(getattr(mutation, "mutation_id", ""))
        for mutation in getattr(technical, "pipeline_mutations", []) or []
        if getattr(mutation, "mutation_id", "")
    }

    base = _reaction_base(tags, outcomes, mutations)
    if base is None:
        return frozenset()

    channels: set[str] = set()
    if "forced_parry" in tags or "force.parry" in mutations:
        channels.add(f"{base}.force_parry")
    if "heal" in tags:
        channels.add(f"{base}.heal")
    if "damage_reduction" in tags or "damage_mult" in mutations:
        channels.add(f"{base}.damage_reduce")
    if "counter_cap" in tags or "counter_to_cap_on_dodge" in mutations:
        channels.add(f"{base}.counter_cap")
    if "counter" in tags or "force_counter_on_parry" in mutations or "force_counter_on_dodge" in mutations:
        channels.add(f"{base}.counter")
    if "parry_boost" in tags:
        channels.add(f"{base}.parry_boost")
    if "debuff" in tags:
        channels.add(f"{base}.debuff")
    if "crit_window" in tags:
        channels.add(f"{base}.crit_window")
    if "converter" in tags:
        channels.add(f"{base}.converter")

    return frozenset(channels)


def _reaction_base(tags: set[str], outcomes: set[str], mutations: set[str]) -> str | None:
    if "parry" in tags or "parry" in outcomes or "force.parry" in mutations or "force_counter_on_parry" in mutations:
        return "next_parry"
    if "dodge" in tags or "dodge" in outcomes or "force_counter_on_dodge" in mutations:
        return "next_dodge"
    if outcomes & {"hit", "crit", "block"}:
        return "next_incoming_hit"
    if "counter_only" in tags:
        return "next_counter"
    return None
