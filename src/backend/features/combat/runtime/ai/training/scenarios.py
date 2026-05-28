"""Synthetic combat scenarios for the MVP offline trainer.

Each scenario is a self-contained tuple of *(bot, candidate_targets,
expected_tags_per_target)*. The expected tag set encodes what a *good*
policy should pick for that target — for example, ``{"anti_parry"}``
means the trainer rewards policies whose chosen action carries the
``anti_parry`` tag against that target.

This is not a full self-play environment. It is a deterministic reward
landscape that the MVP can iterate on without touching the real
:class:`CombatPipeline`. The hand-off to a pipeline-based environment is
the next iteration (see ``docs/ru/backend/combat-ai-policy-training.md``).
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
    stamina: int = 50,
    max_stamina: int = 50,
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

    The ``seed`` is reserved for future random scenario generators; the MVP
    set is deterministic regardless.
    """
    _ = seed  # placeholder for forward compatibility

    scenarios: list[SyntheticScenario] = []

    # 1. High-parry target → anti_parry feint should win.
    bot = _stub_actor(
        "bot_anti_parry",
        team="red",
        is_ai=True,
        hand={"weapon_bind": {"parry": 1, "hit": 1}},
    )
    target = _stub_actor(
        "target_high_parry",
        team="blue",
        hp=80,
        mods={"parry": 0.45, "block": 0.05, "evasion": 0.05},
    )
    scenarios.append(
        SyntheticScenario(
            name="high_parry",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"anti_parry"}))],
        )
    )

    # 2. High-evasion target → anti_evasion feint should win (low_line_step
    #    pays a dodge-token, which adds the anti_evasion tag).
    bot = _stub_actor(
        "bot_anti_dodge",
        team="red",
        is_ai=True,
        hand={"low_line_step": {"dodge": 1, "hit": 1}},
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

    # 3. Multi-target with one anti_parry feint and one high-parry / one
    #    low-defence opponent. Reward feint going to the high-parry one.
    bot = _stub_actor(
        "bot_alloc",
        team="red",
        is_ai=True,
        hand={"weapon_bind": {"parry": 1, "hit": 1}},
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

    # 4. Low-stamina bot → cannot pay the feint activation cost, expected to
    #    fall back to basic attack regardless of target.
    bot = _stub_actor(
        "bot_low_stam",
        team="red",
        is_ai=True,
        stamina=3,
        max_stamina=50,
        hand={"weapon_bind": {"parry": 1, "hit": 1}},
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

    # 5. High-block target with an anti_block-tagged feint (low_line_step
    #    also reduces target block via block_mult). Reward the policy when
    #    the feint is chosen against a high-block opponent.
    bot = _stub_actor(
        "bot_anti_block",
        team="red",
        is_ai=True,
        hand={"low_line_step": {"dodge": 1, "hit": 1}},
    )
    target = _stub_actor(
        "target_high_block",
        team="blue",
        hp=80,
        mods={"block": 0.55, "evasion": 0.05},
    )
    scenarios.append(
        SyntheticScenario(
            name="high_block",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"anti_block"}))],
        )
    )

    return scenarios
