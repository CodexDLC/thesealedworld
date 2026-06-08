import random
import uuid

from src.backend.features.monsters.dto.generation import GeneratedMonster
from src.backend.features.monsters.runtime.group_assembler import GROUP_ASSEMBLY_CONFIG, MonsterGroupAssembler


def _monster(
    variant_key: str,
    threat: int,
    *,
    role: str = "minion",
    gear_score: int | None = None,
    organization_type: str = "swarm",
) -> GeneratedMonster:
    return GeneratedMonster(
        id=uuid.uuid4(),
        clan_id=uuid.uuid4(),
        variant_id=variant_key,
        member_hash=variant_key,
        role=role,
        title=variant_key,
        short_description=variant_key,
        min_tier=1,
        max_tier=7,
        mongo_actor_key=f"actor:{variant_key}",
        active_snapshot={
            "snapshot_tier": 1,
            "raw_gear_score": threat,
            "gear_score": gear_score if gear_score is not None else threat,
            "assembly_cost": gear_score if gear_score is not None else threat,
        },
        actor_document={
            "base_projection": {"organization_type": organization_type},
            "tier_snapshots": {
                "tier_1": {
                    "snapshot_tier": 1,
                    "raw_gear_score": threat,
                    "gear_score": gear_score if gear_score is not None else threat,
                    "assembly_cost": gear_score if gear_score is not None else threat,
                }
            },
        },
    )


def _policy(
    *,
    min_units: int = 1,
    max_units: int = 1,
    start_role: str = "minion",
    allowed_roles: list[str] | None = None,
    role_caps: dict[str, int] | None = None,
    upgrade_order: list[str] | None = None,
    allow_repeated_members: bool = True,
    prefer_distinct_members: bool = False,
) -> dict:
    return {
        "min_units": min_units,
        "max_units": max_units,
        "start_role": start_role,
        "allowed_roles": allowed_roles or ["minion", "veteran", "elite"],
        "role_caps": role_caps or {"minion": max_units, "veteran": max_units, "elite": max_units, "boss": 0},
        "upgrade_order": upgrade_order or ["veteran", "elite"],
        "allow_repeated_members": allow_repeated_members,
        "prefer_distinct_members": prefer_distinct_members,
    }


def test_group_assembler_has_no_family_organization_limits() -> None:
    assert "organizations" not in GROUP_ASSEMBLY_CONFIG


def test_group_assembler_uses_gear_score_as_member_cost() -> None:
    members = [
        _monster("low_threat_expensive", 10, gear_score=200),
        _monster("high_threat_cheap", 100, gear_score=40),
        _monster("mid", 50, gear_score=45),
    ]

    result = MonsterGroupAssembler().assemble(
        members,
        budget=90,
        tier=1,
        danger=0.0,
        composition_policy=_policy(max_units=2, role_caps={"minion": 2, "veteran": 0, "elite": 0, "boss": 0}),
    )

    assert "low_threat_expensive" not in [member.variant_id for member in result.members]
    assert result.total_power <= 90
    assert result.adjusted_budget == 90


def test_group_assembler_does_not_apply_location_danger_budget_bonus() -> None:
    members = [
        _monster("a", 20, gear_score=20, organization_type="solitary"),
        _monster("b", 50, gear_score=50, organization_type="solitary"),
        _monster("c", 150, gear_score=150, organization_type="solitary"),
    ]

    result = MonsterGroupAssembler().assemble(
        members,
        budget=120,
        tier=1,
        danger=1.0,
        composition_policy=_policy(max_units=1),
    )

    assert result.adjusted_budget == 120
    assert [member.variant_id for member in result.members] == ["b"]


def test_group_assembler_swarm_fills_minions_before_upgrading() -> None:
    members = [
        *[_monster(f"m{i}", 20, gear_score=20, organization_type="swarm") for i in range(6)],
        _monster("veteran", 50, role="veteran", gear_score=50, organization_type="swarm"),
        _monster("elite", 150, role="elite", gear_score=150, organization_type="swarm"),
    ]

    result = MonsterGroupAssembler().assemble(
        members,
        budget=160,
        tier=1,
        danger=0.0,
        composition_policy=_policy(max_units=6, role_caps={"minion": 6, "veteran": 6, "elite": 2, "boss": 0}),
    )

    assert [member.role for member in result.members].count("minion") == 6
    assert [member.role for member in result.members].count("veteran") == 0
    assert result.total_power == 120


def test_group_assembler_fills_max_affordable_weak_units_before_upgrading() -> None:
    members = [
        _monster("cheap_cutpurse", 20, role="minion", gear_score=50, organization_type="gang"),
        _monster("armored_thug", 20, role="minion", gear_score=90, organization_type="gang"),
        _monster("hook_veteran", 50, role="veteran", gear_score=80, organization_type="gang"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=200,
        tier=1,
        danger=0.0,
        composition_policy=_policy(max_units=3, role_caps={"minion": 3, "veteran": 3, "elite": 0, "boss": 0}),
    )

    assert len(result.members) == 3
    assert [member.role for member in result.members].count("veteran") == 1
    assert [member.role for member in result.members].count("minion") == 2
    assert result.total_power == 180


def test_group_assembler_does_not_add_upgrade_roles_before_base_group_is_built() -> None:
    members = [
        _monster("camp_rat", 20, role="minion", gear_score=50, organization_type="gang"),
        _monster("raider", 50, role="veteran", gear_score=80, organization_type="gang"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(5)).assemble(
        members,
        budget=120,
        tier=1,
        danger=0.0,
        composition_policy=_policy(max_units=2, role_caps={"minion": 2, "veteran": 1, "elite": 0, "boss": 0}),
    )

    assert len(result.members) == 2
    assert result.total_power == 100
    assert [member.role for member in result.members] == ["minion", "minion"]


def test_group_assembler_pack_fills_minion_slots_before_upgrading() -> None:
    members = [
        *[_monster(f"m{i}", 20, gear_score=20, organization_type="pack") for i in range(4)],
        _monster("veteran", 50, role="veteran", gear_score=50, organization_type="pack"),
        _monster("elite", 150, role="elite", gear_score=150, organization_type="pack"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=150,
        tier=1,
        danger=0.0,
        composition_policy=_policy(max_units=5, role_caps={"minion": 5, "veteran": 3, "elite": 1, "boss": 0}),
    )

    assert [member.role for member in result.members] == ["minion", "minion", "minion", "minion", "minion"]
    assert result.total_power == 100


def test_group_assembler_can_repeat_member_templates_to_fill_budget() -> None:
    members = [
        _monster("cub", 20, gear_score=169, organization_type="pack"),
        _monster("veteran", 50, role="veteran", gear_score=600, organization_type="pack"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=506,
        tier=1,
        danger=0.0,
        composition_policy=_policy(max_units=5, role_caps={"minion": 5, "veteran": 3, "elite": 0, "boss": 0}),
    )

    assert [member.variant_id for member in result.members] == ["cub", "cub"]
    assert result.total_power == 338


def test_group_assembler_uses_weakest_same_role_candidates_for_base_group() -> None:
    members = [
        _monster("cub_a", 20, gear_score=50, organization_type="swarm"),
        _monster("cub_b", 20, gear_score=40, organization_type="swarm"),
        _monster("cub_c", 20, gear_score=60, organization_type="swarm"),
    ]

    policy = _policy(max_units=3, role_caps={"minion": 3, "veteran": 0, "elite": 0, "boss": 0})
    first = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members, budget=170, tier=1, danger=0.0, composition_policy=policy
    )
    second = MonsterGroupAssembler(rng=random.Random(5)).assemble(
        members, budget=170, tier=1, danger=0.0, composition_policy=policy
    )

    assert [member.variant_id for member in first.members] == ["cub_b", "cub_b", "cub_b"]
    assert [member.variant_id for member in second.members] == ["cub_b", "cub_b", "cub_b"]


def test_group_assembler_can_prefer_distinct_member_templates_for_policy_groups() -> None:
    members = [
        _monster("cub_a", 20, gear_score=50, organization_type="swarm"),
        _monster("cub_b", 20, gear_score=40, organization_type="swarm"),
        _monster("cub_c", 20, gear_score=60, organization_type="swarm"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=170,
        tier=1,
        danger=0.0,
        composition_policy={
            "allowed_roles": ["minion"],
            "max_units": 3,
            "allow_repeated_members": True,
            "prefer_distinct_members": True,
        },
    )

    assert [member.variant_id for member in result.members] == ["cub_b", "cub_a", "cub_c"]


def test_group_assembler_repeats_only_after_unique_same_role_candidates_do_not_fit() -> None:
    members = [
        _monster("cheap", 20, gear_score=40, organization_type="swarm"),
        _monster("too_expensive", 20, gear_score=160, organization_type="swarm"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=130,
        tier=1,
        danger=0.0,
        composition_policy=_policy(max_units=3, role_caps={"minion": 3, "veteran": 0, "elite": 0, "boss": 0}),
    )

    assert [member.variant_id for member in result.members] == ["cheap", "cheap", "cheap"]
    assert result.total_power == 120


def test_group_assembler_composition_policy_can_force_boss_only() -> None:
    members = [
        _monster("camp_guard", 20, role="minion", gear_score=20, organization_type="gang"),
        _monster("captain", 90, role="elite", gear_score=90, organization_type="gang"),
        _monster("heart_boss", 180, role="boss", gear_score=180, organization_type="gang"),
    ]

    result = MonsterGroupAssembler().assemble(
        members,
        budget=80,
        tier=1,
        danger=0.0,
        composition_policy={
            "allowed_roles": ["boss"],
            "required_roles": ["boss"],
            "min_units": 1,
            "max_units": 1,
            "allow_repeated_members": False,
        },
    )

    assert [member.variant_id for member in result.members] == ["heart_boss"]
    assert result.total_power == 180


def test_group_assembler_composition_policy_keeps_under_budget_required_boss() -> None:
    members = [
        _monster("guard", 150, role="minion", gear_score=150, organization_type="gang"),
        _monster("tier_two_boss", 800, role="boss", gear_score=800, organization_type="gang"),
    ]

    result = MonsterGroupAssembler().assemble(
        members,
        budget=300,
        tier=1,
        danger=0.0,
        composition_policy={
            "allowed_roles": ["boss"],
            "required_roles": ["boss"],
            "min_units": 1,
            "max_units": 1,
            "allow_repeated_members": False,
        },
    )

    assert [member.variant_id for member in result.members] == ["tier_two_boss"]
    assert result.total_power == 800


def test_group_assembler_composition_policy_limits_transition_roles() -> None:
    members = [
        _monster("minion_a", 20, role="minion", gear_score=20, organization_type="gang"),
        _monster("minion_b", 20, role="minion", gear_score=20, organization_type="gang"),
        _monster("veteran", 45, role="veteran", gear_score=45, organization_type="gang"),
        _monster("elite", 90, role="elite", gear_score=90, organization_type="gang"),
        _monster("boss", 180, role="boss", gear_score=180, organization_type="gang"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=100,
        tier=1,
        danger=0.0,
        composition_policy={
            "allowed_roles": ["minion", "veteran"],
            "max_units": 3,
            "allow_repeated_members": False,
        },
    )

    assert {member.role for member in result.members} <= {"minion", "veteran"}
    assert len(result.members) <= 3
    assert len({member.id for member in result.members}) == len(result.members)


def test_group_assembler_composition_policy_applies_profile_budget_and_role_caps() -> None:
    members = [
        _monster("minion", 10, role="minion", gear_score=10, organization_type="swarm"),
        _monster("veteran", 20, role="veteran", gear_score=20, organization_type="swarm"),
        _monster("elite_a", 30, role="elite", gear_score=30, organization_type="swarm"),
        _monster("elite_b", 30, role="elite", gear_score=30, organization_type="swarm"),
        _monster("boss", 100, role="boss", gear_score=100, organization_type="swarm"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=40,
        tier=1,
        danger=0.0,
        composition_policy={
            "budget_multiplier": 1.25,
            "allowed_roles": ["veteran", "elite"],
            "min_units": 1,
            "max_units": 2,
            "start_role": "veteran",
            "role_caps": {"minion": 0, "veteran": 2, "elite": 1, "boss": 0},
            "upgrade_order": ["elite"],
            "allow_repeated_members": False,
        },
    )

    assert result.target_budget == 50
    assert result.adjusted_budget == 50
    assert {member.role for member in result.members} <= {"veteran", "elite"}
    assert [member.role for member in result.members].count("elite") <= 1
    assert len(result.members) <= 2


def test_group_assembler_ladder_does_not_upgrade_before_base_group_is_full() -> None:
    members = [
        _monster("minion", 20, role="minion", gear_score=224),
        _monster("veteran", 50, role="veteran", gear_score=230),
        _monster("elite", 90, role="elite", gear_score=235),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=235,
        tier=1,
        danger=0.0,
        composition_policy={
            "build_mode": "upgrade_ladder",
            "min_units": 1,
            "max_units": 3,
            "start_role": "minion",
            "allowed_roles": ["minion", "veteran", "elite"],
            "role_caps": {"minion": 3, "veteran": 3, "elite": 1, "boss": 0},
            "upgrade_stages": [
                {"role": "veteran", "requires": {"minion": 3}},
                {"role": "elite", "requires": {"veteran": 3}},
            ],
            "allow_repeated_members": True,
        },
    )

    assert [member.role for member in result.members] == ["minion"]


def test_group_assembler_ladder_requires_veteran_floor_before_elite_upgrade() -> None:
    members = [
        _monster("minion", 20, role="minion", gear_score=40),
        _monster("veteran", 50, role="veteran", gear_score=60),
        _monster("elite", 90, role="elite", gear_score=70),
    ]
    policy = {
        "build_mode": "upgrade_ladder",
        "min_units": 1,
        "max_units": 3,
        "start_role": "minion",
        "allowed_roles": ["minion", "veteran", "elite"],
        "role_caps": {"minion": 3, "veteran": 3, "elite": 1, "boss": 0},
        "upgrade_stages": [
            {"role": "veteran", "requires": {"minion": 3}},
            {"role": "elite", "requires": {"veteran": 3}},
        ],
        "allow_repeated_members": True,
    }

    veteran_floor = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=200,
        tier=1,
        danger=0.0,
        composition_policy=policy,
    )
    elite_upgrade = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=206,
        tier=1,
        danger=0.0,
        composition_policy=policy,
    )

    assert [member.role for member in veteran_floor.members] == ["veteran", "veteran", "veteran"]
    assert [member.role for member in elite_upgrade.members] == ["veteran", "veteran", "elite"]


def test_group_assembler_anchor_and_support_places_leader_before_support() -> None:
    members = [
        _monster("minion", 20, role="minion", gear_score=40),
        _monster("veteran", 50, role="veteran", gear_score=60),
        _monster("elite", 90, role="elite", gear_score=100),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(
        members,
        budget=180,
        tier=1,
        danger=0.0,
        composition_policy={
            "build_mode": "anchor_and_support",
            "min_units": 2,
            "max_units": 3,
            "allowed_roles": ["minion", "veteran", "elite"],
            "required_roles": ["elite"],
            "role_caps": {"minion": 3, "veteran": 2, "elite": 1, "boss": 0},
            "support_roles": ["minion", "veteran"],
            "allow_repeated_members": True,
        },
    )

    assert result.members[0].role == "minion"
    assert [member.role for member in result.members].count("elite") == 1
    assert len(result.members) == 2
