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
    ActiveEffectDTO,
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStats,
    ActorStatusesDTO,
    FeintHandDTO,
)
from src.backend.features.combat.dto.ai_memory_dto import AiMemoryDTO
from src.backend.features.combat.dto.session import BattleContext, BattleMeta
from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO


@dataclass(frozen=True)
class ScenarioTarget:
    target_id: str
    expected_tags: frozenset[str]
    expected_feint_id: str | None = None
    expected_ability_id: str | None = None
    reward_weight: float = 1.0
    resource_penalty: float = 0.1


@dataclass(frozen=True)
class SyntheticScenario:
    """One labelled training example.

    ``battle`` is optional and only set when the scenario needs higher-level
    signals: team awareness (``moves_cache``) or cross-turn memory
    (``ai_memory``). When ``None``, the environment passes ``None`` to
    :meth:`MonsterCombatBrain.decide_turn` so the bot evaluates without
    team/memory context (PR1-style scenarios).
    """

    name: str
    bot: ActorSnapshot
    targets: list[ActorSnapshot]
    expected: list[ScenarioTarget]
    battle: BattleContext | None = None
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
    mods: dict[str, Any] | None = None,
    skills: dict[str, Any] | None = None,
    layout: dict[str, str] | None = None,
    ranged_position: str | None = None,
    is_ai: bool = False,
    effect_ids: list[str] | None = None,
    ai_archetype: str = "balanced",
    en: int = 10,
    max_en: int = 10,
    known_abilities: list[str] | None = None,
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
        en=en,
        max_en=max_en,
        stamina=stamina,
        max_stamina=max_stamina,
        tactics=0,
        tokens=dict(tokens or {}),
        feints=feints,
        ai_archetype=ai_archetype,
    )
    stats = ActorStats(
        mods=CombatModifiersDTO(**(mods or {})),
        skills=CombatSkillsDTO(**(skills or {})),
    )
    effects = [
        ActiveEffectDTO(
            uid=f"uid_{actor_id}_{eid}",
            effect_id=eid,
            source_id=actor_id,
            expire_at_exchange=99,
        )
        for eid in (effect_ids or [])
    ]
    if ranged_position is not None:
        effects.append(
            ActiveEffectDTO(
                uid=f"ranged_position:{actor_id}",
                effect_id="ranged_position",
                source_id=actor_id,
                active_from_exchange=0,
                expire_at_exchange=99,
                params={"position": ranged_position},
            )
        )
    statuses = ActorStatusesDTO(effects=effects)
    return ActorSnapshot(
        meta=meta,
        raw=ActorRawDTO(),
        skills={},
        loadout=ActorLoadoutDTO(layout=dict(layout or {}), known_abilities=list(known_abilities or [])),
        stats=stats,
        statuses=statuses,
    )


def _build_battle(
    actors: list[ActorSnapshot],
    *,
    moves_cache: dict[str, dict] | None = None,
    ai_memory: dict[str, AiMemoryDTO] | None = None,
) -> BattleContext:
    """Construct a minimal BattleContext for scenarios that need team or memory state."""
    return BattleContext(
        session_id=f"scenario_{actors[0].meta.id}",
        meta=BattleMeta(
            active=1,
            step_counter=0,
            active_actors_count=len(actors),
            teams={
                "red": [a.meta.id for a in actors if a.meta.team == "red"],
                "blue": [a.meta.id for a in actors if a.meta.team == "blue"],
            },
            battle_type="arena",
            location_id="arena",
        ),
        actors={str(a.meta.id): a for a in actors},
        moves_cache=dict(moves_cache or {}),
        ai_memory=dict(ai_memory or {}),
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
                ScenarioTarget(target_a.meta.id, frozenset({"anti_parry"}), reward_weight=2.0),
                ScenarioTarget(target_b.meta.id, frozenset(), reward_weight=1.5, resource_penalty=0.2),
            ],
        )
    )

    # 4. Low-stamina bot → cannot pay sword feint activation cost
    #    (5×3=15 stamina); falls back to basic.
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
            expected=[ScenarioTarget(target.meta.id, frozenset(), reward_weight=2.0, resource_penalty=0.25)],
        )
    )

    # =========================================================================
    # PR2: preparation awareness.
    # =========================================================================

    # 7. Target carries prep_counter_on_dodge; bot has a dispel feint
    #    (read_tactic). Reward the dispel choice over a plain attack — attacking
    #    through the prep would invite the counter.
    bot = _stub_actor(
        "bot_dispel",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "read_tactic": {"hit": 1, "block": 2},  # tactical, has dispel_prep tag
        },
    )
    target = _stub_actor(
        "target_with_counter_prep",
        team="blue",
        hp=70,
        mods={"parry": 0.1, "block": 0.05},
        effect_ids=["prep_counter_on_dodge"],
    )
    scenarios.append(
        SyntheticScenario(
            name="prep_threat_dispel",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"dispel_prep"}))],
        )
    )

    # =========================================================================
    # PR3: archetype/tactic stress — not directly scored here because brain
    # applies tactic overlays internally; the scorer naturally rewards the
    # resulting choice. Skip.
    # =========================================================================

    # =========================================================================
    # PR4: team awareness — dedup control on a target an ally already controls.
    # =========================================================================

    # 8. Ally has already queued concussion (control feint) against target.
    #    Bot has its own concussion + a basic. Reward picking the basic.
    bot = _stub_actor(
        "bot_team_dedup",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "concussion": {"block": 3},  # control + shield bash name, normal attack damage
        },
        tokens={"block": 6},  # so concussion is affordable from token side
    )
    ally = _stub_actor("ally_controller", team="red")
    target = _stub_actor(
        "target_already_controlled",
        team="blue",
        hp=70,
        mods={"parry": 0.1, "block": 0.1},
    )
    battle = _build_battle(
        [bot, ally, target],
        moves_cache={
            "ally_controller": {"action": "attack", "target_id": "target_already_controlled", "feint_id": "concussion"}
        },
    )
    scenarios.append(
        SyntheticScenario(
            name="team_dedup_control",
            bot=bot,
            targets=[target],
            # Reward basic, not another control. The higher weight is
            # intentional: this scenario guards the sign of team_dedup_control,
            # where the scorer subtracts a positive magnitude.
            expected=[ScenarioTarget(target.meta.id, frozenset(), reward_weight=2.0, resource_penalty=0.25)],
            battle=battle,
        )
    )

    # =========================================================================
    # PR5: cross-turn memory — observed defence rates override raw stats.
    # =========================================================================

    # 9. Target has *low* raw parry stat but a parry-heavy recent history.
    #    Bot has sword_blade_bind. Reward anti_parry choice via memory signal.
    bot = _stub_actor(
        "bot_observed_parry",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "sword_blade_bind": {"hit": 3, "parry": 2},
        },
    )
    target = _stub_actor(
        "target_behavioural_parry",
        team="blue",
        hp=70,
        mods={"parry": 0.05, "block": 0.05, "evasion": 0.05},
    )
    memory = AiMemoryDTO(
        defence_outcomes=["parry"] * 5 + ["hit"] * 3,  # 0.625 parry rate
    )
    battle = _build_battle(
        [bot, target],
        ai_memory={target.meta.id: memory},
    )
    scenarios.append(
        SyntheticScenario(
            name="observed_parry_rate",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"anti_parry"}))],
            battle=battle,
        )
    )

    # 10. Same shape for evasion: low evasion stat, high observed dodge rate.
    bot = _stub_actor(
        "bot_observed_dodge",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "sword_low_angle": {"hit": 3, "dodge": 2},
        },
    )
    target = _stub_actor(
        "target_behavioural_dodge",
        team="blue",
        hp=70,
        mods={"parry": 0.05, "block": 0.05, "evasion": 0.05},
    )
    memory = AiMemoryDTO(defence_outcomes=["dodge"] * 5 + ["hit"] * 3)
    battle = _build_battle([bot, target], ai_memory={target.meta.id: memory})
    scenarios.append(
        SyntheticScenario(
            name="observed_evasion_rate",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"anti_evasion"}))],
            battle=battle,
        )
    )

    # 11. Same shape for block via the macing_guard_cracker (ignore_block) feint.
    bot = _stub_actor(
        "bot_observed_block",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "macing_guard_cracker": {"hit": 5, "crit": 3},  # ignore_block → anti_block
        },
    )
    target = _stub_actor(
        "target_behavioural_block",
        team="blue",
        hp=70,
        mods={"parry": 0.05, "block": 0.05, "evasion": 0.05},
    )
    memory = AiMemoryDTO(defence_outcomes=["block"] * 5 + ["hit"] * 3)
    battle = _build_battle([bot, target], ai_memory={target.meta.id: memory})
    scenarios.append(
        SyntheticScenario(
            name="observed_block_rate",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"anti_block"}))],
            battle=battle,
        )
    )

    # 12. Repeat-feint penalty: same anti_parry feint already in feints_used.
    #     Bot has two equivalent anti_parry feints; reward picking the *fresh*
    #     one (sword_low_angle is anti_evasion not anti_parry, so we use a
    #     different feint pair: sword_blade_bind and macing_break_stance both
    #     carry anti_parry, but only the latter is fresh in memory).
    bot = _stub_actor(
        "bot_repeat_feint",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "sword_blade_bind": {"hit": 3, "parry": 2},  # anti_parry, recently used
            "macing_break_stance": {"hit": 3, "parry": 5},  # anti_parry, fresh
        },
        tokens={"hit": 6, "parry": 6, "crit": 4},
    )
    target = _stub_actor(
        "target_high_parry_for_variety",
        team="blue",
        hp=80,
        mods={"parry": 0.5, "block": 0.05},
    )
    my_memory = AiMemoryDTO(feints_used=["sword_blade_bind"] * 3)
    battle = _build_battle([bot, target], ai_memory={bot.meta.id: my_memory})
    scenarios.append(
        SyntheticScenario(
            name="variety_after_repeat",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"anti_parry"}),
                    expected_feint_id="macing_break_stance",
                )
            ],
            battle=battle,
        )
    )

    # 13. Stamina discipline: two anti-parry feints are useful, but the
    #     cheaper one should win over the expensive variant.
    bot = _stub_actor(
        "bot_stamina_discipline",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "sword_blade_bind": {"hit": 3, "parry": 2},
            "macing_break_stance": {"hit": 3, "parry": 5},
        },
        tokens={"hit": 6, "parry": 6},
    )
    target = _stub_actor("target_stamina_soft", team="blue", hp=80, mods={"parry": 0.45})
    scenarios.append(
        SyntheticScenario(
            name="stamina_discipline",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"anti_parry"}),
                    expected_feint_id="sword_blade_bind",
                    reward_weight=2.0,
                    resource_penalty=0.2,
                )
            ],
        )
    )

    # 14. Sticky target signal fixture. The current production brain plans per
    #     committed target, so this is mostly a guardrail fixture for future
    #     target-selection training rather than a strong reward axis today.
    bot = _stub_actor(
        "bot_sticky_target",
        team="red",
        is_ai=True,
        stamina=60,
        hand={"measured_strike": {"hit": 3}},
    )
    previous = _stub_actor("sticky_previous", team="blue", hp=80, mods={"parry": 0.05})
    other = _stub_actor("sticky_other", team="blue", hp=80, mods={"parry": 0.05})
    battle = _build_battle(
        [bot, previous, other],
        ai_memory={bot.meta.id: AiMemoryDTO(last_target_id=previous.meta.id)},
    )
    scenarios.append(
        SyntheticScenario(
            name="sticky_target_focus",
            bot=bot,
            targets=[previous, other],
            expected=[
                ScenarioTarget(
                    previous.meta.id,
                    frozenset({"damage_tag"}),
                ),
                ScenarioTarget(other.meta.id, frozenset()),
            ],
            battle=battle,
            metadata={"note": "Per-target planner fixture; sticky bias is constant per target today."},
        )
    )

    # 15. Gift token neutral drift guard: carrying gift tokens alone should not
    #     make the policy prefer spending an unrelated feint.
    bot = _stub_actor(
        "bot_gift_neutral",
        team="red",
        is_ai=True,
        stamina=60,
        tokens={"gift": 2},
        hand={"measured_strike": {"hit": 3}},
    )
    target = _stub_actor("target_gift_neutral", team="blue", hp=20, mods={"parry": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="gift_resource_neutral",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset(), reward_weight=1.5, resource_penalty=0.2)],
        )
    )

    # 16-19. Archetype stress fixtures. Archetype JSON overlays remain
    #     hand-authored in this iteration; these scenarios keep the training
    #     corpus explicit about the intended behaviour surfaces.
    bot = _stub_actor(
        "bot_berserker_damage",
        team="red",
        is_ai=True,
        ai_archetype="berserker",
        stamina=60,
        hand={"measured_strike": {"hit": 3}, "sword_clean_path": {"hit": 3, "crit": 5}},
    )
    target = _stub_actor("target_berserker_damage", team="blue", hp=80, mods={"parry": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="archetype_berserker_damage",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"damage_tag"}),
                    expected_feint_id="sword_clean_path",
                )
            ],
        )
    )

    bot = _stub_actor(
        "bot_bulwark_survival",
        team="red",
        is_ai=True,
        ai_archetype="bulwark",
        hp=20,
        stamina=60,
        hand={"measured_strike": {"hit": 3}, "second_breath": {"parry": 5}},
    )
    target = _stub_actor("target_bulwark_safe", team="blue", hp=80, mods={"parry": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="archetype_bulwark_survival",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"heal"}), expected_feint_id="second_breath")],
        )
    )

    bot = _stub_actor(
        "bot_tactician_dispel",
        team="red",
        is_ai=True,
        ai_archetype="tactician",
        stamina=60,
        hand={"measured_strike": {"hit": 3}, "read_tactic": {"hit": 1, "block": 2}},
    )
    target = _stub_actor(
        "target_tactician_prep",
        team="blue",
        hp=80,
        mods={"parry": 0.05},
        effect_ids=["prep_full_defense"],
    )
    scenarios.append(
        SyntheticScenario(
            name="archetype_tactician_dispel",
            bot=bot,
            targets=[target],
            expected=[ScenarioTarget(target.meta.id, frozenset({"dispel_prep"}), expected_feint_id="read_tactic")],
        )
    )

    bot = _stub_actor(
        "bot_duelist_counter_defence",
        team="red",
        is_ai=True,
        ai_archetype="duelist",
        stamina=60,
        hand={"measured_strike": {"hit": 3}, "sword_blade_bind": {"hit": 3, "parry": 2}},
    )
    target = _stub_actor("target_duelist_parry", team="blue", hp=80, mods={"parry": 0.45})
    scenarios.append(
        SyntheticScenario(
            name="archetype_duelist_counter_defence",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"anti_parry"}),
                    expected_feint_id="sword_blade_bind",
                )
            ],
        )
    )

    # =========================================================================
    # PR6: multi-target / swarm cleanup fixtures.
    #
    # Each scenario pairs a single-target option with a true AoE feint from
    # the post-overhaul catalog. expected_tags uses the semantic
    # ``multi_target`` tag derived in ``feint_tags`` from ``target_count > 1``.
    # AoE feint stamina cost = sum(cost.values()) * FEINT_STAMINA_PER_TOKEN
    # (= 3), so bots get enough stamina to afford the AoE in every case.
    # =========================================================================

    # 20. arrow_rain (cost 5+2=7 → 21 stamina): archery swarm cleanup.
    bot = _stub_actor(
        "bot_arrow_rain",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "snap_shot": {"hit": 3},
            "arrow_rain": {"hit": 5, "crit": 2},
        },
        tokens={"hit": 6, "crit": 4},
    )
    target_a = _stub_actor("swarm_archer_a", team="blue", hp=40, mods={"parry": 0.05})
    target_b = _stub_actor("swarm_archer_b", team="blue", hp=40, mods={"parry": 0.05})
    target_c = _stub_actor("swarm_archer_c", team="blue", hp=40, mods={"parry": 0.05})
    target_d = _stub_actor("swarm_archer_d", team="blue", hp=40, mods={"parry": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="arrow_rain_swarm",
            bot=bot,
            targets=[target_a, target_b, target_c, target_d],
            expected=[
                ScenarioTarget(target_a.meta.id, frozenset({"multi_target"}), expected_feint_id="arrow_rain"),
                ScenarioTarget(target_b.meta.id, frozenset({"damage_tag"})),
                ScenarioTarget(target_c.meta.id, frozenset({"damage_tag"})),
                ScenarioTarget(target_d.meta.id, frozenset({"damage_tag"})),
            ],
        )
    )

    # 21. ranged_covering_volley (cost 4+2=6 → 18 stamina): tactical ranged position-fire.
    bot = _stub_actor(
        "bot_covering_volley",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "snap_shot": {"hit": 3},
            "ranged_covering_volley": {"hit": 4, "tempo": 2},
        },
        tokens={"hit": 5, "tempo": 4},
    )
    target_a = _stub_actor("volley_target_a", team="blue", hp=50, mods={"parry": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="ranged_covering_fire_position",
            bot=bot,
            targets=[target_a],
            expected=[
                ScenarioTarget(
                    target_a.meta.id,
                    frozenset({"damage_tag"}),
                    expected_feint_id="ranged_covering_volley",
                ),
            ],
        )
    )

    # 21a. Archer is trapped in close range. The resolver makes close the
    # worst bow position and the only range where counters are reachable, so
    # the trainer should value a real distance reset over a plain shot.
    bot = _stub_actor(
        "bot_archer_close_open",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "snap_shot": {"hit": 3},
            "open_distance": {"dodge": 5, "tempo": 2},
            "backstep_shot": {"hit": 2, "dodge": 3},
        },
        tokens={"hit": 5, "dodge": 7, "tempo": 4},
        skills={"skill_archery": 0.75, "skill_ranged_combat": 0.75},
        layout={"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"},
        ranged_position="close",
    )
    target = _stub_actor(
        "target_close_counter_entry",
        team="blue",
        hp=85,
        mods={"counter_attack_chance": 0.45, "initiative": 12.0},
    )
    scenarios.append(
        SyntheticScenario(
            name="archer_close_open_distance",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"ranged_reposition", "ranged_keep_far"}),
                    expected_feint_id="open_distance",
                    reward_weight=2.0,
                )
            ],
        )
    )

    # 21b. From mid range, a cheaper backstep shot is enough: improve current
    # position and keep firing instead of spending the full distance reset.
    bot = _stub_actor(
        "bot_archer_mid_backstep",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "snap_shot": {"hit": 3},
            "backstep_shot": {"hit": 2, "dodge": 3},
            "open_distance": {"dodge": 5, "tempo": 2},
        },
        tokens={"hit": 5, "dodge": 7, "tempo": 3},
        skills={"skill_archery": 0.7, "skill_ranged_combat": 0.7},
        layout={"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"},
        ranged_position="mid",
    )
    target = _stub_actor("target_mid_entry", team="blue", hp=85, mods={"counter_attack_chance": 0.15})
    scenarios.append(
        SyntheticScenario(
            name="archer_mid_backstep_shot",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"ranged_reposition"}),
                    expected_feint_id="backstep_shot",
                    reward_weight=1.5,
                )
            ],
        )
    )

    # 21c. At far range, the archer should cash in the positional damage
    # bonus instead of paying to move again.
    bot = _stub_actor(
        "bot_archer_far_covering",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "snap_shot": {"hit": 3},
            "open_distance": {"dodge": 5, "tempo": 2},
            "ranged_covering_volley": {"hit": 4, "tempo": 2},
        },
        tokens={"hit": 6, "dodge": 5, "tempo": 5},
        skills={"skill_archery": 0.8, "skill_ranged_combat": 0.8},
        layout={"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"},
        ranged_position="far",
    )
    target = _stub_actor("target_far_lane", team="blue", hp=90, mods={"counter_attack_chance": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="archer_far_covering_fire",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"ranged_position_damage"}),
                    expected_feint_id="ranged_covering_volley",
                    reward_weight=1.5,
                )
            ],
        )
    )

    # 21d. A close-range shield target is especially hostile to the archer:
    # guard power raises mitigation and close range allows counter pressure.
    bot = _stub_actor(
        "bot_archer_close_shield_escape",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "snap_shot": {"hit": 3},
            "open_distance": {"dodge": 5, "tempo": 2},
            "ranged_covering_volley": {"hit": 4, "tempo": 2},
        },
        tokens={"hit": 6, "dodge": 7, "tempo": 5},
        skills={"skill_archery": 0.75, "skill_ranged_combat": 0.75},
        layout={"main_hand": "skill_archery", "tactical_style": "skill_ranged_combat"},
        ranged_position="close",
    )
    target = _stub_actor(
        "target_close_shield_counter",
        team="blue",
        hp=90,
        mods={"counter_attack_chance": 0.35, "shield_guard_power": 32.0},
        skills={"skill_shield_mastery": 0.8},
        layout={"off_hand": "skill_shield_mastery", "tactical_style": "skill_shield_mastery"},
    )
    scenarios.append(
        SyntheticScenario(
            name="archer_close_shield_counter_escape",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"ranged_reposition", "ranged_keep_far"}),
                    expected_feint_id="open_distance",
                    reward_weight=2.0,
                )
            ],
        )
    )

    # 21e. New shield resolver folds guard power into mitigation. Armor-bypass
    # training must see that shield guard behaves like a real damage gate even
    # when legacy ``block`` is low.
    bot = _stub_actor(
        "bot_shield_guard_crush",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "macing_heavy_line": {"hit": 3},
            "macing_armor_crush": {"hit": 3, "crit": 2},
        },
        tokens={"hit": 5, "crit": 3},
    )
    target = _stub_actor(
        "target_guard_armor",
        team="blue",
        hp=90,
        mods={"armor": 8.0, "block": 0.05, "shield_guard_power": 36.0},
        skills={"skill_shield_mastery": 0.85},
        layout={"off_hand": "skill_shield_mastery", "tactical_style": "skill_shield_mastery"},
    )
    scenarios.append(
        SyntheticScenario(
            name="shield_guard_armor_bypass",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"armor_bypass"}),
                    expected_feint_id="macing_armor_crush",
                    reward_weight=1.5,
                )
            ],
        )
    )

    # 21f. Shield mastery no longer maps cleanly to raw ``block``. Teach the
    # policy that guard-cracking still matters when shield guard + mastery are
    # the resolver's real block pressure.
    bot = _stub_actor(
        "bot_shield_mastery_cracker",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "macing_heavy_line": {"hit": 3},
            "sword_blade_bind": {"hit": 3, "parry": 2},
            "macing_guard_cracker": {"hit": 5, "crit": 3},
        },
        tokens={"hit": 6, "parry": 3, "crit": 4},
    )
    target = _stub_actor(
        "target_mastery_guard",
        team="blue",
        hp=90,
        mods={"block": 0.05, "parry": 0.05, "shield_guard_power": 34.0},
        skills={"skill_shield_mastery": 0.9},
        layout={"off_hand": "skill_shield_mastery", "tactical_style": "skill_shield_mastery"},
    )
    scenarios.append(
        SyntheticScenario(
            name="shield_mastery_block_pressure",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"anti_block"}),
                    expected_feint_id="macing_guard_cracker",
                    reward_weight=1.5,
                )
            ],
        )
    )

    # 22. polearm_line_cleave (cost 4+1=5 → 15 stamina): polearm 3-target cleave.
    bot = _stub_actor(
        "bot_polearm_cleave",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "polearm_long_line": {"hit": 3},
            "polearm_line_cleave": {"hit": 4, "parry": 1},
        },
        tokens={"hit": 6, "parry": 3},
    )
    target_a = _stub_actor("cleave_target_a", team="blue", hp=60, mods={"parry": 0.05})
    target_b = _stub_actor("cleave_target_b", team="blue", hp=60, mods={"parry": 0.05})
    target_c = _stub_actor("cleave_target_c", team="blue", hp=60, mods={"parry": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="polearm_line_swarm",
            bot=bot,
            targets=[target_a, target_b, target_c],
            expected=[
                ScenarioTarget(
                    target_a.meta.id,
                    frozenset({"multi_target"}),
                    expected_feint_id="polearm_line_cleave",
                ),
                ScenarioTarget(target_b.meta.id, frozenset({"damage_tag"})),
                ScenarioTarget(target_c.meta.id, frozenset({"damage_tag"})),
            ],
        )
    )

    # 23. two_handed_whirl (cost 5+2=7 → 21 stamina): tactical 2H AoE.
    bot = _stub_actor(
        "bot_two_handed_whirl",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "two_handed_whirl": {"hit": 5, "parry": 2},
        },
        tokens={"hit": 6, "parry": 4},
    )
    target_a = _stub_actor("whirl_target_a", team="blue", hp=45, mods={"parry": 0.1, "block": 0.05})
    target_b = _stub_actor("whirl_target_b", team="blue", hp=45, mods={"parry": 0.1, "block": 0.05})
    target_c = _stub_actor("whirl_target_c", team="blue", hp=45, mods={"parry": 0.1, "block": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="two_handed_whirl_swarm",
            bot=bot,
            targets=[target_a, target_b, target_c],
            expected=[
                ScenarioTarget(
                    target_a.meta.id,
                    frozenset({"multi_target"}),
                    expected_feint_id="two_handed_whirl",
                ),
                ScenarioTarget(target_b.meta.id, frozenset({"damage_tag"})),
                ScenarioTarget(target_c.meta.id, frozenset({"damage_tag"})),
            ],
        )
    )

    # 24. dual_blade_whirl (cost 5+3=8 → 24 stamina): tactical dual-wield AoE.
    bot = _stub_actor(
        "bot_dual_blade_whirl",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "dual_blade_whirl": {"hit": 5, "dodge": 3},
        },
        tokens={"hit": 6, "dodge": 5},
    )
    target_a = _stub_actor("dual_target_a", team="blue", hp=45, mods={"parry": 0.05})
    target_b = _stub_actor("dual_target_b", team="blue", hp=45, mods={"parry": 0.05})
    target_c = _stub_actor("dual_target_c", team="blue", hp=45, mods={"parry": 0.05})
    target_d = _stub_actor("dual_target_d", team="blue", hp=45, mods={"parry": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="dual_blade_whirl_swarm",
            bot=bot,
            targets=[target_a, target_b, target_c, target_d],
            expected=[
                ScenarioTarget(
                    target_a.meta.id,
                    frozenset({"multi_target"}),
                    expected_feint_id="dual_blade_whirl",
                ),
                ScenarioTarget(target_b.meta.id, frozenset({"damage_tag"})),
                ScenarioTarget(target_c.meta.id, frozenset({"damage_tag"})),
                ScenarioTarget(target_d.meta.id, frozenset({"damage_tag"})),
            ],
        )
    )

    # 25. overkill_waste_vs_aoe: a single-target finisher (sword_clean_path,
    #     cost 3+5=8 → 24 stamina) competes with a true AoE (two_handed_whirl).
    #     Three low-HP soft targets are present. The trainer rewards the AoE
    #     choice so the policy learns that one big overkill swing is wasted
    #     when a cleave clears the wave.
    bot = _stub_actor(
        "bot_overkill_choice",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "sword_clean_path": {"hit": 3, "crit": 5},
            "two_handed_whirl": {"hit": 5, "parry": 2},
        },
        tokens={"hit": 6, "crit": 5, "parry": 4},
    )
    target_a = _stub_actor("overkill_target_a", team="blue", hp=18, mods={"parry": 0.05})
    target_b = _stub_actor("overkill_target_b", team="blue", hp=18, mods={"parry": 0.05})
    target_c = _stub_actor("overkill_target_c", team="blue", hp=18, mods={"parry": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="overkill_waste_vs_aoe",
            bot=bot,
            targets=[target_a, target_b, target_c],
            expected=[
                ScenarioTarget(
                    target_a.meta.id,
                    frozenset({"multi_target"}),
                    expected_feint_id="two_handed_whirl",
                ),
                ScenarioTarget(target_b.meta.id, frozenset({"damage_tag"})),
                ScenarioTarget(target_c.meta.id, frozenset({"damage_tag"})),
            ],
        )
    )

    # =========================================================================
    # PR6: anti-defence axes derived from semantic mutations only.
    # =========================================================================

    # 26. high_dodge_anti_evasion_semantic: explicit guardrail that the chosen
    #     feint must carry ``anti_evasion`` from a pipeline_mutation
    #     (``target_evasion_mult`` < 1.0 on sword_low_angle) and not from any
    #     token-cost heuristic. Duplicates the existing high_evasion test
    #     but with a softer alternative in hand so the trainer cannot win
    #     by ranking on cost.
    bot = _stub_actor(
        "bot_anti_evasion_semantic",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "sword_low_angle": {"hit": 3, "dodge": 2},  # target_evasion_mult=0.85 → anti_evasion
            "wind_dance": {"dodge": 5},  # pure prep — NO anti_evasion despite dodge tokens
        },
        tokens={"hit": 5, "dodge": 5},
    )
    target = _stub_actor(
        "target_high_evasion_semantic",
        team="blue",
        hp=80,
        mods={"evasion": 0.45},
    )
    scenarios.append(
        SyntheticScenario(
            name="high_dodge_anti_evasion_semantic",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"anti_evasion"}),
                    expected_feint_id="sword_low_angle",
                )
            ],
        )
    )

    # 27. armor_bypass_vs_heavy: macing_armor_crush triggers
    #     ``flat_armor_penetration_bonus_pct`` → ``armor_bypass`` tag.
    #     Heavy-armor target with high block to make plain hits less appealing.
    bot = _stub_actor(
        "bot_armor_bypass",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "macing_heavy_line": {"hit": 3},
            "macing_armor_crush": {"hit": 3, "crit": 2},
        },
        tokens={"hit": 5, "crit": 3},
    )
    target = _stub_actor(
        "target_heavy_armor",
        team="blue",
        hp=80,
        mods={"armor": 30.0, "block": 0.20, "parry": 0.05},
    )
    scenarios.append(
        SyntheticScenario(
            name="armor_bypass_vs_heavy",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"armor_bypass"}),
                    expected_feint_id="macing_armor_crush",
                )
            ],
        )
    )

    # 28. shield_block_pressure: high raw block stat (no memory signal).
    #     macing_guard_cracker carries ``anti_block`` from ``ignore_block``
    #     pipeline mutation. Pair with a parry-target alternative to verify
    #     the policy selects on the actual defence rather than picking the
    #     more expensive option by default.
    bot = _stub_actor(
        "bot_shield_pressure",
        team="red",
        is_ai=True,
        stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "sword_blade_bind": {"hit": 3, "parry": 2},  # anti_parry, not the right axis
            "macing_guard_cracker": {"hit": 5, "crit": 3},  # anti_block, right axis
        },
        tokens={"hit": 6, "parry": 4, "crit": 4},
    )
    target = _stub_actor(
        "target_high_block",
        team="blue",
        hp=80,
        mods={"block": 0.45, "parry": 0.05, "evasion": 0.05},
    )
    scenarios.append(
        SyntheticScenario(
            name="shield_block_pressure",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"anti_block"}),
                    expected_feint_id="macing_guard_cracker",
                )
            ],
        )
    )

    # 29. aoe_stamina_discipline: bot has a true AoE feint but not enough
    #     stamina to activate it (two_handed_whirl needs 21; bot has 18).
    #     ``build_legal_actions_for_target`` filters the AoE out, so the
    #     policy must fall back to the basic. Reward staying on
    #     ``measured_strike`` with no AoE expectation — guards against the
    #     trainer learning a "always pick the AoE if a swarm is visible"
    #     shortcut that ignores stamina.
    bot = _stub_actor(
        "bot_aoe_stamina_discipline",
        team="red",
        is_ai=True,
        stamina=18,
        max_stamina=60,
        hand={
            "measured_strike": {"hit": 3},
            "two_handed_whirl": {"hit": 5, "parry": 2},
        },
        tokens={"hit": 6, "parry": 4},
    )
    target_a = _stub_actor("stam_swarm_a", team="blue", hp=40, mods={"parry": 0.05})
    target_b = _stub_actor("stam_swarm_b", team="blue", hp=40, mods={"parry": 0.05})
    target_c = _stub_actor("stam_swarm_c", team="blue", hp=40, mods={"parry": 0.05})
    scenarios.append(
        SyntheticScenario(
            name="aoe_stamina_discipline",
            bot=bot,
            targets=[target_a, target_b, target_c],
            expected=[
                ScenarioTarget(target_a.meta.id, frozenset({"damage_tag"}), expected_feint_id="measured_strike"),
                ScenarioTarget(target_b.meta.id, frozenset({"damage_tag"})),
                ScenarioTarget(target_c.meta.id, frozenset({"damage_tag"})),
            ],
        )
    )

    # 30. basic instant heal: blood/block/gift should be converted into a
    #     survival buff before the exchange when the bot is wounded. The
    #     exchange still happens afterwards; the expected ability target is the bot itself.
    bot = _stub_actor(
        "bot_basic_blood_heal",
        team="red",
        is_ai=True,
        hp=25,
        max_hp=100,
        en=20,
        max_en=20,
        tokens={"blood": 3, "block": 1, "gift": 1},
        known_abilities=["basic_wipe_blood"],
    )
    target = _stub_actor("target_basic_blood_heal", team="blue", hp=80)
    scenarios.append(
        SyntheticScenario(
            name="basic_blood_heal",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    bot.meta.id,
                    frozenset({"heal"}),
                    expected_ability_id="basic_wipe_blood",
                ),
                ScenarioTarget(target.meta.id, frozenset({"damage_tag"})),
            ],
        )
    )

    # 31. basic instant anti-defence: tempo+hit should be spent on the stance
    #     break against a dodgy target, then the exchange still proceeds.
    bot = _stub_actor(
        "bot_basic_break_stance",
        team="red",
        is_ai=True,
        en=20,
        max_en=20,
        stamina=60,
        tokens={"tempo": 3, "hit": 2},
        known_abilities=["basic_break_stance"],
    )
    target = _stub_actor("target_basic_break_stance", team="blue", hp=80, mods={"evasion": 0.45})
    scenarios.append(
        SyntheticScenario(
            name="basic_break_stance_instant",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"debuff", "anti_evasion"}),
                    expected_ability_id="basic_break_stance",
                ),
                ScenarioTarget(target.meta.id, frozenset({"damage_tag"})),
            ],
        )
    )

    # 32. basic instant stamina discipline: two tactical instants are legal, but
    #     the lower-token anti-defence option should win on a non-finishable
    #     target. This prevents stamina_cost from drifting positive just because
    #     instant abilities are generally useful.
    bot = _stub_actor(
        "bot_basic_stamina_discipline",
        team="red",
        is_ai=True,
        stamina=60,
        tokens={"tempo": 3, "hit": 2, "crit": 2},
        known_abilities=["basic_break_stance", "basic_expose_weakness"],
    )
    target = _stub_actor("target_basic_stamina_discipline", team="blue", hp=80)
    scenarios.append(
        SyntheticScenario(
            name="basic_stamina_discipline",
            bot=bot,
            targets=[target],
            expected=[
                ScenarioTarget(
                    target.meta.id,
                    frozenset({"debuff", "anti_evasion"}),
                    expected_ability_id="basic_break_stance",
                    reward_weight=2.0,
                    resource_penalty=0.25,
                ),
                ScenarioTarget(target.meta.id, frozenset({"damage_tag"})),
            ],
        )
    )

    return scenarios
