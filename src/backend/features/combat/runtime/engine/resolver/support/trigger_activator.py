"""Trigger rule dispatch — chance, effect application, token grants.

Canonical implementation used by Step-классы (Phase 4). ``CombatResolver``
retains a parallel implementation during Phase 3 so that existing tests that
monkeypatch ``_bonus_token_roll`` keep working when reaching token grants via
``cls._apply_trigger_token_grants``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto.pipeline import (
    CombatTriggerActivationDTO,
    CombatTriggerAttemptDTO,
    CombatTriggerFactDTO,
)
from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.engine.math_core import MathCore
from src.backend.features.combat.runtime.engine.pipeline_mutation_service import PipelineMutationService

from . import token_awarder

if TYPE_CHECKING:
    from src.backend.features.combat.dto.actor import ActorStats
    from src.backend.features.combat.dto.pipeline import InteractionResultDTO, PipelineContextDTO


def select_trigger_activation(
    ctx: PipelineContextDTO, rule_id: str, rule_data: dict[str, Any]
) -> CombatTriggerActivationDTO | None:
    activations = ctx.trigger_activations.get(rule_id) or [
        CombatTriggerActivationDTO(trigger_id=rule_id, source="system")
    ]
    allowed_sources = set(rule_data.get("allowed_sources") or [])
    if not allowed_sources:
        return activations[0]

    for activation in activations:
        if activation.source in allowed_sources:
            return activation
    return None


def trigger_chance(rule_data: dict[str, Any], *, source_stats: ActorStats | None = None) -> float:
    raw_chance = rule_data.get("chance", 0.0)
    chance = float(raw_chance) if isinstance(raw_chance, (int, float)) else 0.0

    skill_key = rule_data.get("chance_skill_key")
    if source_stats is not None and isinstance(skill_key, str) and skill_key:
        raw_scale = rule_data.get("chance_skill_scale", 0.0)
        scale = float(raw_scale) if isinstance(raw_scale, (int, float)) else 0.0
        chance += max(0.0, getattr(source_stats.skills, skill_key, 0.0)) * scale

    raw_cap = rule_data.get("chance_cap")
    if isinstance(raw_cap, (int, float)):
        chance = min(chance, float(raw_cap))

    return max(0.0, chance)


def apply_trigger_effects(
    ctx: PipelineContextDTO,
    res: InteractionResultDTO,
    activation: CombatTriggerActivationDTO,
    rule_id: str,
    rule_data: dict[str, Any],
    *,
    step_key: str,
) -> None:
    for effect_id in rule_data.get("applied_effect_ids", []):
        effect_data = {"id": effect_id, "source_trigger_id": rule_id}
        if step_key == "ON_CRIT":
            conditions = effect_data.setdefault("conditions", {})
            conditions.setdefault("is_hit", True)
            conditions.setdefault("is_crit", True)
        res.applied_effects.append(effect_data)

    if activation.source != "weapon" or not activation.source_slot:
        return

    for payload in ctx.trigger_effect_payloads.get(activation.source_slot, []):
        if not isinstance(payload, dict):
            continue
        effect_id = payload.get("id") or payload.get("effect_id")
        if not isinstance(effect_id, str):
            continue
        effect_data = dict(payload)
        effect_data["id"] = effect_id
        effect_data.setdefault("source_trigger_id", rule_id)
        if step_key == "ON_CRIT":
            conditions = effect_data.setdefault("conditions", {})
            conditions.setdefault("is_hit", True)
            conditions.setdefault("is_crit", True)
        res.applied_effects.append(effect_data)


def apply_trigger_token_grants(res: InteractionResultDTO, rule_data: dict[str, Any]) -> None:
    attacker_tokens = rule_data.get("token_grants_attacker", [])
    defender_tokens = rule_data.get("token_grants_defender", [])
    for token in attacker_tokens:
        token_awarder.award_attacker_token(res, str(token))
    for token in defender_tokens:
        token_awarder.award_defender_token(res, str(token))


def resolve_triggers(
    ctx: PipelineContextDTO,
    res: InteractionResultDTO,
    step_key: str,
    *,
    source_stats: ActorStats | None = None,
) -> None:
    """Dispatch trigger rules for ``step_key`` against the trigger DTO sections."""
    dto_section: Any = None
    if step_key == "ON_ACCURACY_CHECK" or step_key == "ON_MISS":
        dto_section = ctx.triggers.accuracy
    elif step_key == "ON_CRIT" or step_key == "ON_CRIT_FAIL":
        dto_section = ctx.triggers.crit
    elif step_key in {"ON_PRE_EVASION", "ON_DODGE", "ON_DODGE_FAIL"}:
        dto_section = ctx.triggers.dodge
    elif step_key == "ON_PARRY" or step_key == "ON_PARRY_FAIL":
        dto_section = ctx.triggers.parry
    elif step_key == "ON_BLOCK" or step_key == "ON_BLOCK_FAIL":
        dto_section = ctx.triggers.block
    elif step_key == "ON_CHECK_CONTROL":
        dto_section = ctx.triggers.control
    elif step_key == "ON_DAMAGE":
        dto_section = ctx.triggers.damage

    if not dto_section:
        return

    active_rule_ids = [k for k, v in dto_section.model_dump().items() if v is True]
    if not active_rule_ids:
        return

    for rule_id in active_rule_ids:
        rule_data = CombatCatalogIntegrator.get_trigger_rule(rule_id)
        if not rule_data:
            continue
        if rule_data.get("event") != step_key:
            continue

        activation = select_trigger_activation(ctx, rule_id, rule_data)
        if activation is None:
            continue

        chance = trigger_chance(rule_data, source_stats=source_stats)
        roll, passed = MathCore.roll_chance(chance)
        tags = [*activation.tags, *[str(tag) for tag in rule_data.get("tags", [])]]
        res.trigger_attempts.append(
            CombatTriggerAttemptDTO(
                trigger_id=rule_id,
                event=step_key,
                source=activation.source,
                source_id=activation.source_id,
                source_slot=activation.source_slot,
                chance=chance,
                roll=roll,
                passed=passed,
                display_policy=str(rule_data.get("display_policy") or "merge"),
                stacking_rule=str(rule_data.get("stacking_rule") or "unique"),
                tags=tags,
            )
        )

        if not passed:
            continue

        res.fired_triggers.append(rule_id)
        res.trigger_facts.append(
            CombatTriggerFactDTO(
                trigger_id=rule_id,
                event=step_key,
                source=activation.source,
                source_id=activation.source_id,
                source_slot=activation.source_slot,
                chance=chance,
                display_policy=str(rule_data.get("display_policy") or "merge"),
                stacking_rule=str(rule_data.get("stacking_rule") or "unique"),
                tags=tags,
            )
        )

        PipelineMutationService.apply(
            applications=rule_data.get("pipeline_mutations", []),
            ctx=ctx,
            source=activation.source,
            source_id=activation.source_id or rule_id,
        )
        apply_trigger_effects(ctx, res, activation, rule_id, rule_data, step_key=step_key)
        apply_trigger_token_grants(res, rule_data)
