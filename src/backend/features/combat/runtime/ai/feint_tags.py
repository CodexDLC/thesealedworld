"""Semantic tag derivation for a feint catalog entry.

This module is the single source of truth for the AI's action tags. The
tags are derived **only** from semantic fields of ``FeintTechnicalDTO``:

* ``applicability_tags`` — designer-authored intent.
* ``pipeline_mutations`` — runtime contract effects (e.g. lowers target
  parry, ignores block, bypasses flat armor).
* ``modifier_applications`` — self-buff/self-debuff numeric modifiers.
* ``effects`` — debuffs/controls applied to the target on hit.
* ``preparation_effects`` — self-buffs/preparations applied to the source.
* ``shield_guard_damage_*`` — shield-bash damage signal.
* ``purchase_group`` and ``target_count`` — structural facets.

The previous derivation used ``cost.tactics`` token slots as a proxy for
counter-defence intent (e.g. paying a ``dodge`` token implied
``anti_evasion``). That mixed *resource type* with *effect semantics* and
was demonstrably wrong on pure preparation feints (e.g. ``wind_dance``
costs ``dodge:5`` but does not counter evasion in any sense). The
``cost.tactics`` mapping is intentionally not consulted here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import (
    PipelineMutationApplicationDTO,
    get_pipeline_mutation_contract,
)

if TYPE_CHECKING:
    from src.backend.features.game_catalog.combat.resources.feints.schemas import FeintCatalogEntryDTO

# Applicability tags that mark a feint as an attack vector (deserves the
# ``damage_tag`` so the scorer treats it on the same axis as a basic attack).
_DAMAGE_INTENT_APPLICABILITY: frozenset[str] = frozenset(
    {"hit", "crit", "damage", "forced_crit", "bonus_damage", "accuracy"}
)

# Pipeline mutations that *bypass* a specific defence layer when truthy.
_BYPASS_PARRY_MUTATIONS: frozenset[str] = frozenset({"ignore_parry"})
_BYPASS_EVASION_MUTATIONS: frozenset[str] = frozenset({"ignore_evasion"})
_BYPASS_BLOCK_MUTATIONS: frozenset[str] = frozenset({"ignore_block"})

# Effect id substring hints (only on effects with target_actor == "target").
_CONTROL_EFFECT_HINTS: tuple[str, ...] = (
    "stun",
    "root",
    "freeze",
    "knockdown",
    "concussion",
    "no_feints",
    "blind",
    "fear",
)


def derive_feint_tags(entry: FeintCatalogEntryDTO | None, feint_id: str) -> frozenset[str]:
    """Return the AI's action tags for one feint catalog entry.

    Returns an empty set when ``entry`` is ``None`` (unknown feint id). The
    caller (``action_space``) is responsible for adding a baseline tag for
    the plain ``attack`` action and for unknown feints.
    """
    if entry is None:
        return frozenset()

    tech = entry.technical
    tags: set[str] = set()

    # 1. Designer-authored applicability tags pass through verbatim.
    applicability_set: set[str] = {str(t) for t in (tech.applicability_tags or [])}
    tags.update(applicability_set)

    # 2. Attack-vector intent from applicability semantics.
    if applicability_set & _DAMAGE_INTENT_APPLICABILITY:
        tags.add("damage_tag")

    # 3. Modifier applications — only crit_chance_add marks an attack vector.
    # parry_mult / evasion_mult here are self-buffs (target_actor defaults to
    # "self") and must NOT be read as anti-X.
    for app in tech.modifier_applications or []:
        if str(app.modifier_id) == "crit_chance_add":
            tags.add("damage_tag")

    # 4. Pipeline mutations — primary semantic source for anti-X and armor_bypass.
    for app in tech.pipeline_mutations or []:
        mid = str(app.mutation_id)
        value = _resolve_mutation_value(app)

        if mid == "target_parry_mult" and isinstance(value, (int, float)) and value < 1.0:
            tags.add("anti_parry")
        elif mid == "target_evasion_mult" and isinstance(value, (int, float)) and value < 1.0:
            tags.add("anti_evasion")
        elif mid == "target_block_mult" and isinstance(value, (int, float)) and value < 1.0:
            tags.add("anti_block")
        elif mid in _BYPASS_PARRY_MUTATIONS and bool(value):
            tags.add("anti_parry")
        elif mid in _BYPASS_EVASION_MUTATIONS and bool(value):
            tags.add("anti_evasion")
        elif mid in _BYPASS_BLOCK_MUTATIONS and bool(value):
            tags.add("anti_block")
        elif "flat_armor" in mid or "armor_penetration" in mid or mid == "ignore_armor":
            if bool(value):
                tags.add("armor_bypass")
        elif mid in {"accuracy_mult", "damage_mult"} and isinstance(value, (int, float)) and value > 1.0:
            tags.add("damage_tag")
        elif "crit" in mid:
            # force.crit, crit_damage_boost, etc. — all attack-vector mutations.
            tags.add("damage_tag")

    # 5. Effects with target_actor == "target" → debuff/control/bleed/dispel_prep.
    for effect in tech.effects or []:
        if not isinstance(effect, dict):
            continue
        target_actor = str(effect.get("target_actor") or "target")
        if target_actor != "target":
            continue
        effect_id = str(effect.get("id") or "").lower()
        tags.add("debuff")
        if "dispel_preparation" in effect_id:
            tags.add("dispel_prep")
        if any(hint in effect_id for hint in _CONTROL_EFFECT_HINTS):
            tags.add("control")
        if "bleed" in effect_id:
            tags.add("bleed")

    # 6. Preparation effects on source → self_buff + specific prep_* tags + heal.
    for prep in tech.preparation_effects or []:
        if not isinstance(prep, dict):
            continue
        target_actor = str(prep.get("target_actor") or "source")
        if target_actor != "source":
            continue
        tags.add("self_buff")
        prep_id = str(prep.get("id") or "").lower()
        params = prep.get("params") or {}
        if isinstance(params, dict) and any(str(k).startswith("heal_") for k in params):
            tags.add("heal")
        if "counter" in prep_id:
            tags.add("prep_counter")
        if "riposte" in prep_id:
            tags.add("prep_riposte")
        if "defense" in prep_id:
            tags.add("prep_defense")
        if "parry" in prep_id:
            tags.add("prep_parry")
        if "dodge" in prep_id:
            tags.add("prep_dodge")

    # 7. Shield-guard damage → shield_damage + damage_tag.
    shield_ratio = float(getattr(tech, "shield_guard_damage_ratio", 0.0) or 0.0)
    shield_min = int(getattr(tech, "shield_guard_damage_min", 0) or 0)
    if shield_ratio > 0.0 or shield_min > 0:
        tags.add("shield_damage")
        tags.add("damage_tag")

    # 8. Purchase group — structural facet.
    group = getattr(tech, "purchase_group", None) or "basic"
    tags.add(f"group_{group}")

    # 9. Multi-target flag.
    if int(getattr(tech, "target_count", 1) or 1) > 1:
        tags.add("multi_target")

    return frozenset(tags)


def _resolve_mutation_value(app: PipelineMutationApplicationDTO) -> Any:
    """Resolve effective mutation value: override first, then contract default."""
    override = getattr(app, "value_override", None)
    if override is not None:
        return override
    contract = get_pipeline_mutation_contract(str(app.mutation_id))
    return contract.default_value if contract is not None else None
