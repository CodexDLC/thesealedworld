"""Pin-down test for CombatResolver trigger event contract.

Locks the set of trigger event names that the resolver may emit via
``_resolve_triggers``. If a refactor accidentally drops a `_resolve_triggers`
call (or introduces a new event name), this test will catch it.

Note: ``ON_DAMAGE`` is defined in ``triggers/schemas.py`` (and dispatched in
``_resolve_triggers``), but the resolver does not currently emit it from any
step — that branch is dormant by design.

This test is intentionally coarse: it does not validate semantic correctness
of triggers, only the *set* of event names observed across a representative
set of resolver paths. Detailed assertions live in ``test_runtime_processors``.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from src.backend.features.combat.dto import (
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    CombatMoveDTO,
    ExchangePayload,
    PipelineContextDTO,
)
from src.backend.features.combat.dto.actor import ActorStats
from src.backend.features.combat.runtime.engine.ability_service import AbilityService
from src.backend.features.combat.runtime.engine.resolver import CombatResolver
from src.backend.features.combat.runtime.engine.resolver.support import trigger_activator
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO

EXPECTED_TRIGGER_EVENTS: frozenset[str] = frozenset(
    {
        "ON_ACCURACY_CHECK",
        "ON_MISS",
        "ON_CRIT",
        "ON_CRIT_FAIL",
        "ON_PRE_EVASION",
        "ON_DODGE",
        "ON_DODGE_FAIL",
        "ON_PARRY",
        "ON_PARRY_FAIL",
        "ON_BLOCK",
        "ON_BLOCK_FAIL",
        "ON_CHECK_CONTROL",
    }
)


def _actor(actor_id: int, team: str) -> ActorSnapshot:
    return ActorSnapshot(
        meta=ActorMetaDTO(
            id=actor_id,
            name=f"A{actor_id}",
            type="player",
            team=team,
            hp=100,
            max_hp=100,
            stamina=100,
            max_stamina=100,
        ),
        raw=ActorRawDTO(modifiers={"main_hand_damage_base": 200, "main_hand_accuracy": 1.0}),
        loadout=ActorLoadoutDTO(layout={"main_hand": "skill_swords"}),
    )


def _stats(mods: dict[str, float] | None = None) -> ActorStats:
    return ActorStats(
        mods=CombatModifiersDTO(**(mods or {})),
        skills=CombatSkillsDTO(),
    )


def _build_ctx(source: ActorSnapshot, target: ActorSnapshot) -> PipelineContextDTO:
    move = CombatMoveDTO(
        move_id="m_pin",
        char_id=source.char_id,
        strategy="exchange",
        payload=ExchangePayload(target_id=target.char_id),
    )
    ctx = PipelineContextDTO()
    ctx.result.source_id = source.char_id
    ctx.result.target_id = target.char_id
    AbilityService().pre_process(ctx, move, source, target)
    return ctx


def _run_scenario(configure: Callable[[PipelineContextDTO], None]) -> list[str]:
    """Run a single resolve_exchange and collect every step_key passed to _resolve_triggers."""
    source = _actor(1, "a")
    target = _actor(2, "b")
    source.stats = _stats({"main_hand_accuracy": 1.0})
    target.stats = _stats()

    ctx = _build_ctx(source, target)
    configure(ctx)

    observed: list[str] = []
    original = trigger_activator.resolve_triggers

    def spy(ctx_, res_, step_key, *, source_stats=None):
        observed.append(step_key)
        return original(ctx_, res_, step_key, source_stats=source_stats)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(trigger_activator, "resolve_triggers", spy)
        CombatResolver.resolve_exchange(source.stats, target.stats, ctx)

    return observed


@pytest.mark.unit
def test_resolver_emits_exactly_the_contracted_trigger_event_set() -> None:
    """Union of scenarios must equal EXPECTED_TRIGGER_EVENTS — no more, no less."""
    observed: set[str] = set()

    def _miss(ctx: PipelineContextDTO) -> None:
        # Natural accuracy fail (not force.miss — that path bypasses ON_MISS by design).
        ctx.mods.accuracy_mult = 0.0

    def _hit_critfail_dodge(ctx: PipelineContextDTO) -> None:
        ctx.flags.force.hit = True
        ctx.flags.restriction.cannot_crit = True
        ctx.flags.force.dodge = True

    def _hit_crit_dodgefail_parry(ctx: PipelineContextDTO) -> None:
        ctx.flags.force.hit = True
        ctx.flags.force.crit = True
        ctx.flags.force.hit_evasion = True
        ctx.flags.force.parry = True

    def _hit_dodgefail_parryfail_block(ctx: PipelineContextDTO) -> None:
        ctx.flags.force.hit = True
        ctx.flags.restriction.cannot_crit = True
        ctx.flags.force.hit_evasion = True
        ctx.flags.restriction.ignore_parry = True
        ctx.flags.force.block = True
        # ON_BLOCK only emits when the shield-block branch resolves to "counter"
        # (the defense branch is a passive mitigation, not a trigger event).
        ctx.flags.formula.force_shield_counter_branch = True

    def _hit_through_to_damage(ctx: PipelineContextDTO) -> None:
        ctx.flags.force.hit = True
        ctx.flags.restriction.cannot_crit = True
        ctx.flags.force.hit_evasion = True
        ctx.flags.restriction.ignore_parry = True
        ctx.flags.restriction.ignore_block = True

    for configure in (
        _miss,
        _hit_critfail_dodge,
        _hit_crit_dodgefail_parry,
        _hit_dodgefail_parryfail_block,
        _hit_through_to_damage,
    ):
        observed.update(_run_scenario(configure))

    assert observed == EXPECTED_TRIGGER_EVENTS, (
        f"Trigger event contract mismatch.\n"
        f"  Missing (regression):   {EXPECTED_TRIGGER_EVENTS - observed}\n"
        f"  Unexpected (new event): {observed - EXPECTED_TRIGGER_EVENTS}"
    )
