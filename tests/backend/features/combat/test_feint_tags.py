"""Unit tests for :func:`derive_feint_tags`.

Asserts the contract called out in the PR1 plan:

* Cost tokens never produce ``anti_evasion`` / ``anti_parry`` / ``anti_block``
  / ``damage_tag`` on their own.
* Pure preparation feints (e.g. ``wind_dance``) carry NO attack-vector tag.
* Every attacking feint (weapon school + basic hit) keeps ``damage_tag``.
* anti-X tags come strictly from ``pipeline_mutations`` resolved values,
  ``ignore_*`` flags, or designer-authored ``applicability_tags``.
* Effects, preparation effects, and shield-guard damage round out the
  semantic vocabulary.
* :func:`_resolve_mutation_value` honours ``value_override`` first and falls
  back to the contract default value.
"""

from __future__ import annotations

import pytest

from src.backend.features.combat.integrations import CombatCatalogIntegrator
from src.backend.features.combat.runtime.ai.action_space import (
    build_legal_actions_for_target,
)
from src.backend.features.combat.runtime.ai.feint_tags import (
    _resolve_mutation_value,
    derive_feint_tags,
)
from src.backend.features.game_catalog.combat.resources.common.pipeline_mutations import (
    PipelineMutationApplicationDTO,
)


def _tags(feint_id: str) -> frozenset[str]:
    entry = CombatCatalogIntegrator.get_feint_catalog_entry(feint_id)
    assert entry is not None, f"feint {feint_id!r} not found in catalog"
    return derive_feint_tags(entry, feint_id)


# ---------------------------------------------------------------------------
# 1. Cost-derived sanity: pure prep feints lose anti-X and damage_tag.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_wind_dance_has_no_anti_evasion() -> None:
    """``wind_dance`` is a dodge-slot preparation, not a counter-evasion feint.

    Before PR1 the ``dodge`` token in its cost falsely produced
    ``anti_evasion``. After PR1 the tag must be absent.
    """
    tags = _tags("wind_dance")
    assert "anti_evasion" not in tags
    assert "anti_parry" not in tags
    assert "anti_block" not in tags


@pytest.mark.unit
def test_wind_dance_has_no_damage_tag() -> None:
    """Pure preparation feints must not compete with the basic attack on the
    expected-damage axis."""
    assert "damage_tag" not in _tags("wind_dance")


@pytest.mark.unit
def test_glancing_step_has_no_damage_tag() -> None:
    assert "damage_tag" not in _tags("glancing_step")


@pytest.mark.unit
def test_blade_dance_emits_prep_counter_only() -> None:
    tags = _tags("blade_dance")
    assert "prep_counter" in tags
    assert "self_buff" in tags
    assert "prep_dodge" in tags
    assert "damage_tag" not in tags
    assert "anti_evasion" not in tags


@pytest.mark.unit
def test_foresight_parry_has_no_damage_tag_or_anti_parry() -> None:
    tags = _tags("foresight_parry")
    assert "damage_tag" not in tags
    assert "anti_parry" not in tags
    assert "prep_parry" in tags
    assert "self_buff" in tags


# ---------------------------------------------------------------------------
# 2. anti-X from real semantic sources.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sword_blade_bind_anti_parry_from_pipeline_mutation() -> None:
    """``sword_blade_bind`` lowers target parry via ``target_parry_mult=0.85``."""
    tags = _tags("sword_blade_bind")
    assert "anti_parry" in tags
    # Also has the applicability tag, but the pipeline mutation alone is sufficient.
    assert "damage_tag" in tags


@pytest.mark.unit
def test_sword_low_angle_anti_evasion_from_target_evasion_mult() -> None:
    tags = _tags("sword_low_angle")
    assert "anti_evasion" in tags
    assert "damage_tag" in tags


@pytest.mark.unit
def test_macing_guard_cracker_anti_block_from_ignore_block() -> None:
    """``ignore_block`` pipeline mutation marks the feint as anti_block even
    when the contract default for the mutation is ``True``."""
    tags = _tags("macing_guard_cracker")
    assert "anti_block" in tags
    assert "damage_tag" in tags


@pytest.mark.unit
def test_fencing_inside_line_anti_parry_from_ignore_parry() -> None:
    tags = _tags("fencing_inside_line")
    assert "anti_parry" in tags
    assert "damage_tag" in tags


@pytest.mark.unit
def test_fencing_hidden_entry_anti_evasion_and_damage_tag() -> None:
    """Forces a crit and lowers target evasion → both anti_evasion and damage_tag."""
    tags = _tags("fencing_hidden_entry")
    assert "anti_evasion" in tags
    assert "damage_tag" in tags


# ---------------------------------------------------------------------------
# 3. armor_bypass from ignore_flat_armor / armor_penetration variants.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fencing_needle_gap_armor_bypass_from_ignore_flat_armor() -> None:
    tags = _tags("fencing_needle_gap")
    assert "armor_bypass" in tags
    assert "damage_tag" in tags


@pytest.mark.unit
def test_macing_armor_crush_armor_bypass_from_flat_armor_penetration() -> None:
    tags = _tags("macing_armor_crush")
    assert "armor_bypass" in tags
    assert "damage_tag" in tags


@pytest.mark.unit
def test_piercing_arrow_armor_bypass_from_boost_flat_armor_penetration() -> None:
    tags = _tags("piercing_arrow")
    assert "armor_bypass" in tags
    assert "damage_tag" in tags


# ---------------------------------------------------------------------------
# 4. damage_tag fallback: parametrized over every catalogued attacking feint.
# ---------------------------------------------------------------------------


_ATTACKING_FEINTS: tuple[str, ...] = (
    # basic_hit
    "measured_strike",
    "steady_strike",
    "flawless_strike",
    # weapon_swords
    "sword_measured_line",
    "sword_blade_bind",
    "sword_hard_bind",
    "sword_low_angle",
    "sword_cut_angle",
    "sword_open_line",
    "sword_clean_path",
    # weapon_fencing
    "fencing_precise_prick",
    "fencing_corner_entry",
    "fencing_hidden_entry",
    "fencing_gap_probe",
    "fencing_needle_gap",
    "fencing_slip_guard",
    "fencing_inside_line",
    # weapon_macing
    "macing_heavy_line",
    "macing_armor_crush",
    "macing_skullbreaker",
    "macing_break_swing",
    "macing_break_stance",
    "macing_guard_cracker",
    # weapon_polearms
    "polearm_long_line",
    "polearm_hook_step",
    "polearm_leg_sweep",
    "polearm_guard_intercept",
    "polearm_stunning_intercept",
    "polearm_pinning_point",
    "polearm_locked_distance",
    # weapon_archery
    "snap_shot",
    "headshot",
    "piercing_arrow",
    "precise_weak_spot",
    "quiet_weak_spot",
    "blood_aim_crit",
)


@pytest.mark.unit
@pytest.mark.parametrize("feint_id", _ATTACKING_FEINTS)
def test_every_attacking_feint_keeps_damage_tag(feint_id: str) -> None:
    """After removing token-derived ``damage_tag``, every attacking feint
    must still earn ``damage_tag`` from applicability_tags, pipeline_mutations,
    or shield_guard damage. This is the regression guard for PR1."""
    assert "damage_tag" in _tags(feint_id), (
        f"{feint_id} lost damage_tag — attacking feints will be down-scored "
        "against the basic attack baseline."
    )


# ---------------------------------------------------------------------------
# 5. action_space-level: basic attack still carries damage_tag (not via feint_tags).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_action_space_basic_attack_has_damage_tag() -> None:
    """``build_legal_actions_for_target`` must always emit a basic attack
    candidate carrying ``damage_tag``, independent of any feint catalog."""
    from src.backend.features.combat.dto.actor import (
        ActorLoadoutDTO,
        ActorMetaDTO,
        ActorRawDTO,
        ActorSnapshot,
        ActorStats,
        FeintHandDTO,
    )
    from src.shared.schemas.modifier_dto import CombatModifiersDTO, CombatSkillsDTO

    def _actor(actor_id: str, team: str) -> ActorSnapshot:
        return ActorSnapshot(
            meta=ActorMetaDTO(
                id=actor_id,
                name=actor_id,
                type="monster",
                team=team,
                is_ai=True,
                hp=100,
                max_hp=100,
                en=10,
                max_en=10,
                stamina=50,
                max_stamina=50,
                tactics=0,
                tokens={},
                feints=FeintHandDTO(hand={}, arsenal=[]),
            ),
            raw=ActorRawDTO(),
            skills={},
            loadout=ActorLoadoutDTO(),
            stats=ActorStats(mods=CombatModifiersDTO(), skills=CombatSkillsDTO()),
        )

    bot = _actor("bot", "red")
    target = _actor("t1", "blue")
    actions = build_legal_actions_for_target(bot, target)

    assert len(actions) == 1
    assert actions[0].feint_id is None
    assert "damage_tag" in actions[0].tags


# ---------------------------------------------------------------------------
# 6. Effects: dispel_prep / control / shield bash / bleed.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_read_tactic_dispel_prep() -> None:
    tags = _tags("read_tactic")
    assert "dispel_prep" in tags
    assert "debuff" in tags
    assert "damage_tag" not in tags  # has no hit/crit/damage applicability tag


@pytest.mark.unit
def test_concussion_control_and_attack_damage() -> None:
    tags = _tags("concussion")
    assert "control" in tags  # control tag from applicability + concussed_no_feints effect
    assert "debuff" in tags
    assert "shield_bash" in tags
    assert "shield_damage" not in tags
    assert "damage_tag" in tags


@pytest.mark.unit
def test_polearm_leg_sweep_control_from_knockdown_effect() -> None:
    tags = _tags("polearm_leg_sweep")
    assert "control" in tags
    assert "debuff" in tags
    assert "damage_tag" in tags


# ---------------------------------------------------------------------------
# 7. Preparation effects: heal, self_buff, prep_counter / prep_riposte / etc.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_second_breath_heal_and_self_buff() -> None:
    tags = _tags("second_breath")
    assert "heal" in tags
    assert "self_buff" in tags
    assert "damage_tag" not in tags
    assert "anti_parry" not in tags


@pytest.mark.unit
def test_perfect_riposte_heal_and_prep_riposte() -> None:
    tags = _tags("2h_perfect_riposte")
    assert "heal" in tags
    assert "self_buff" in tags
    assert "prep_riposte" in tags


@pytest.mark.unit
def test_active_defense_prep_defense_self_buff() -> None:
    tags = _tags("active_defense")
    assert "self_buff" in tags
    assert "prep_defense" in tags
    assert "damage_tag" not in tags


# ---------------------------------------------------------------------------
# 8. Unknown feint → empty tag set (action_space fallback is responsible for damage_tag).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unknown_feint_returns_empty_set() -> None:
    assert derive_feint_tags(None, "definitely_not_a_feint") == frozenset()


# ---------------------------------------------------------------------------
# 9. _resolve_mutation_value: override priority, fallback to contract default.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_resolve_mutation_value_uses_value_override_when_present() -> None:
    app = PipelineMutationApplicationDTO(mutation_id="target_parry_mult", value_override=0.65)
    assert _resolve_mutation_value(app) == 0.65


@pytest.mark.unit
def test_resolve_mutation_value_falls_back_to_contract_default_when_no_override() -> None:
    # ``ignore_block`` contract default_value is True; no override given.
    app = PipelineMutationApplicationDTO(mutation_id="ignore_block")
    assert _resolve_mutation_value(app) is True


@pytest.mark.unit
def test_resolve_mutation_value_returns_none_for_unknown_mutation() -> None:
    app = PipelineMutationApplicationDTO(mutation_id="nonexistent_mutation_id_xyz")
    assert _resolve_mutation_value(app) is None


# ---------------------------------------------------------------------------
# 10. multi_target: AoE feints must derive ``multi_target`` from target_count > 1.
# These are the swarm-cleanup feints used by the PR6 training scenarios.
# ---------------------------------------------------------------------------


_AOE_FEINTS: tuple[str, ...] = (
    "arrow_rain",
    "polearm_line_cleave",
    "two_handed_whirl",
    "dual_blade_whirl",
)


@pytest.mark.unit
@pytest.mark.parametrize("feint_id", _AOE_FEINTS)
def test_aoe_feint_has_multi_target_tag(feint_id: str) -> None:
    """Each canonical AoE feint must carry ``multi_target`` so the trainer
    can reward swarm-cleanup choices. Lack of this tag would force the
    training corpus to use a side channel (e.g. cost penalties) to encode
    AoE intent, which is exactly what feint_tags PR1 fixed."""
    assert "multi_target" in _tags(feint_id), (
        f"{feint_id} lost multi_target — PR6 swarm scenarios cannot reward it."
    )


@pytest.mark.unit
@pytest.mark.parametrize("feint_id", _AOE_FEINTS)
def test_aoe_feint_keeps_damage_tag(feint_id: str) -> None:
    """multi_target is additive: AoE feints must still compete on the
    damage axis against single-target attacks."""
    assert "damage_tag" in _tags(feint_id), f"{feint_id} lost damage_tag despite AoE applicability"


# ---------------------------------------------------------------------------
# 11. ranged position semantics: tactical-ranged mutations must become
# trainable tags, not only opaque resolver action_facts.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_open_distance_emits_ranged_reposition_and_keep_far_tags() -> None:
    tags = _tags("open_distance")
    assert {"ranged_reposition", "ranged_keep_far"} <= tags


@pytest.mark.unit
def test_covering_position_emits_ranged_stabilize_tag() -> None:
    tags = _tags("covering_position")
    assert "ranged_stabilize" in tags
    assert "ranged_keep_far" in tags


@pytest.mark.unit
def test_backstep_shot_emits_ranged_reposition_tag() -> None:
    tags = _tags("backstep_shot")
    assert "ranged_reposition" in tags
    assert "damage_tag" in tags


@pytest.mark.unit
def test_blinding_shot_emits_ranged_pressure_reduce_tag() -> None:
    assert "ranged_pressure_reduce" in _tags("blinding_shot")


@pytest.mark.unit
def test_ranged_covering_volley_emits_position_damage_tag() -> None:
    tags = _tags("ranged_covering_volley")
    assert "ranged_position_damage" in tags
    assert "damage_tag" in tags
