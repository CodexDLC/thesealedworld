"""Synthetic combat scenarios for the MVP offline trainer.

Each scenario is a self-contained tuple of *(bot, candidate_targets,
expected_tags_per_target)*. The expected tag set encodes what a *good*
policy should pick for that target — for example, ``{"anti_parry"}``
means the trainer rewards policies whose chosen action carries the
``anti_parry`` tag against that target.

All feint IDs below exist in the post-overhaul catalog under
``src/backend/features/game_catalog/combat/resources/feints/definitions``.

This is not a full self-play environment. It is a deterministic reward
landscape that the MVP can iterate on without touching the real
:class:`CombatPipeline`. The hand-off to a pipeline-based environment is
the next iteration (see ``docs/ru/backend/features/combat/runtime/ai.md``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.backend.features.combat.dto.actor import (
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStats,
    FeintHandDTO,
)
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


@dataclass(frozen=True)
class ScenarioTarget:
    target_id: str
    expected_tags: frozenset[str]


@dataclass(frozen=True)
class SyntheticScenario:
    """One labelled training example."""

    name: str
    bot: ActorSnapshot
    targets: list[ActorSnapshot]
    expected: list[ScenarioTarget]
    metadata: dict[str, Any] = field(default_factory=dict)


def _stub_actor(
    actor_id: str,
    *,
    team: str,
    hp: int = 100,
    max_hp: int = 100,
    stamina: int = 60,
    max_stamina: int = 60,
    tokens: dict[str, int] | None = None,
    hand: dict[str, dict[str, int]] | None = None,
    mods: dict[str, float] | None = None,
    is_ai: bool = False,
) -> ActorSnapshot:
    feints = FeintHandDTO(hand=dict(hand or {}), arsenal=list((hand or {}).keys()))
    meta = ActorMetaDTO(
        id=actor_id,
        name=actor_id,
        type="monster" if is_ai else "player",
        team=team,
        is_ai=is_ai,
        hp=hp,
        max_hp=max_hp,
        en=10,
        max_en=10,
        stamina=stamina,
        max_stamina=max_stamina,
        tactics=0,
        tokens=dict(tokens or {}),
        feints=feints,
    )
    stats = ActorStats(
        mods=CombatModifiersDTO(**(mods or {})),
        skills=CombatSkillsDTO(),
    )
    return ActorSnapshot(
        meta=meta,
        raw=ActorRawDTO(),
        skills={},
        loadout=ActorLoadoutDTO(),
        stats=stats,
    )


def default_scenario_set(seed: int = 0) -> list[SyntheticScenario]:
    """Hand-crafted scenarios covering the main tactical axes.

    Each scenario uses real feint IDs from the post-overhaul catalog so the
    reward landscape is meaningful end-to-end (catalog → tags → scorer).
    """
    _ = seed  # placeholder for forward compatibility

    scenarios: list[SyntheticScenario] = []

    # 1. High-parry target with a parry-paying weapon feint.
    #    sword_blade_bind costs hit:3+parry:2 → anti_parry tag from parry token.
    bot = _stub_actor(
        "bot_anti_parry",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},  # basic (no defence tag)
            "sword_blade_bind": {"hit": 3, "parry": 2},  # weapon, anti_parry
        },
    )
    target = _stub_actor(
        "target_high_parry",
        team="blue",
        hp=80,
        mods={"parry": 0.45, "block": 0.05},
    )
    scenarios.append(
        SyntheticScenario(
            name="high_parry",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"anti_parry"}))],
        )
    )

    # 2. High-evasion target → sword_low_angle (hit:3+dodge:2) tags anti_evasion.
    bot = _stub_actor(
        "bot_anti_dodge",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "sword_low_angle": {"hit": 3, "dodge": 2},
        },
    )
    target = _stub_actor(
        "target_high_evasion",
        team="blue",
        hp=80,
        mods={"evasion": 0.45},
    )
    scenarios.append(
        SyntheticScenario(
            name="high_evasion",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"anti_evasion"}))],
        )
    )

    # 3. Multi-target with one anti-parry weapon feint shared between two
    #    targets. Reward feint going to the high-parry one, basic to the soft one.
    bot = _stub_actor(
        "bot_alloc",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "sword_blade_bind": {"hit": 3, "parry": 2},
        },
    )
    target_a = _stub_actor(
        "alloc_high_parry",
        team="blue",
        hp=70,
        mods={"parry": 0.45},
    )
    target_b = _stub_actor(
        "alloc_low_def",
        team="blue",
        hp=70,
        mods={"parry": 0.05},
    )
    scenarios.append(
        SyntheticScenario(
            name="allocate_anti_parry",
            bot=bot,
            targets=[target_a, target_b],
            expected=[
                ScenarioTarget(target_a.meta.id, frozenset({"anti_parry"})),
                ScenarioTarget(target_b.meta.id, frozenset()),
            ],
        )
    )

    # 4. Low-stamina bot → cannot pay sword feint activation cost
    #    (5×5=25 stamina); falls back to basic.
    bot = _stub_actor(
        "bot_low_stam",
        team="red",
        is_ai=True,
        stamina=12,
        max_stamina=60,
        hand={
            "sword_blade_bind": {"hit": 3, "parry": 2},
        },
    )
    target = _stub_actor(
        "target_any",
        team="blue",
        hp=70,
        mods={"parry": 0.5},
    )
    scenarios.append(
        SyntheticScenario(
            name="low_stamina_save",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset())],
        )
    )

    # 5. Wounded bot with a heal-prep parry feint in hand: expected to use it.
    #    second_breath costs parry:5; applicability_tags include "heal" and
    #    preparation_effects carry heal_* params → action_space emits `heal`.
    bot = _stub_actor(
        "bot_wounded",
        team="red",
        is_ai=True,
        hp=20,
        max_hp=100,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "second_breath": {"parry": 5},
        },
    )
    target = _stub_actor(
        "target_safe",
        team="blue",
        hp=70,
        mods={"parry": 0.05, "block": 0.05},
    )
    scenarios.append(
        SyntheticScenario(
            name="wounded_bot_heal",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"heal"}))],
        )
    )

    # 6. Finishable target with a cheap basic and an expensive weapon feint;
    #    don't burn an 8-token feint on a dying target — basic is the right call.
    bot = _stub_actor(
        "bot_finisher",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "sword_clean_path": {"hit": 3, "crit": 5},  # very expensive
        },
    )
    target = _stub_actor(
        "target_dying",
        team="blue",
        hp=12,
        mods={"parry": 0.05, "block": 0.05},
    )
    scenarios.append(
        SyntheticScenario(
            name="finishable_cheap_kill",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset())],
        )
    )

    return scenarios
