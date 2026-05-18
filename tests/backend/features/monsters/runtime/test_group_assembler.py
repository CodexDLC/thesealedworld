import random
import uuid

from src.backend.features.monsters.dto.generation import GeneratedMonster
from src.backend.features.monsters.runtime.group_assembler import MonsterGroupAssembler


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
        variant_key=variant_key,
        role=role,
        member_tier=0,
        threat_rating=threat,
        name_ru=variant_key,
        description=variant_key,
        text_content={},
        scaled_attributes={"endurance": 1},
        scaled_skills={},
        items={},
        vitals={},
        ai_profile={},
        generation_meta={
            "balance": {
                "gear_score": gear_score if gear_score is not None else threat,
                "organization_type": organization_type,
            }
        },
    )


def test_group_assembler_uses_gear_score_as_member_cost() -> None:
    members = [
        _monster("low_threat_expensive", 10, gear_score=200),
        _monster("high_threat_cheap", 100, gear_score=40),
        _monster("mid", 50, gear_score=45),
    ]

    result = MonsterGroupAssembler().assemble(members, budget=90, tier=1, danger=0.0)

    assert "low_threat_expensive" not in [member.variant_key for member in result.members]
    assert result.total_power <= 90
    assert result.adjusted_budget == 90


def test_group_assembler_applies_danger_budget_bonus() -> None:
    members = [
        _monster("a", 20, gear_score=20, organization_type="solitary"),
        _monster("b", 50, gear_score=50, organization_type="solitary"),
        _monster("c", 150, gear_score=150, organization_type="solitary"),
    ]

    result = MonsterGroupAssembler().assemble(members, budget=120, tier=1, danger=1.0)

    assert result.adjusted_budget == 150
    assert [member.variant_key for member in result.members] == ["c"]


def test_group_assembler_swarm_fills_minions_before_upgrading() -> None:
    members = [
        *[_monster(f"m{i}", 20, gear_score=20, organization_type="swarm") for i in range(6)],
        _monster("veteran", 50, role="veteran", gear_score=50, organization_type="swarm"),
        _monster("elite", 150, role="elite", gear_score=150, organization_type="swarm"),
    ]

    result = MonsterGroupAssembler().assemble(members, budget=160, tier=1, danger=0.0)

    assert [member.role for member in result.members].count("minion") == 6
    assert [member.role for member in result.members].count("veteran") == 0
    assert result.total_power == 120


def test_group_assembler_pack_fills_minion_slots_before_upgrading() -> None:
    members = [
        *[_monster(f"m{i}", 20, gear_score=20, organization_type="pack") for i in range(4)],
        _monster("veteran", 50, role="veteran", gear_score=50, organization_type="pack"),
        _monster("elite", 150, role="elite", gear_score=150, organization_type="pack"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(members, budget=150, tier=1, danger=0.0)

    assert [member.role for member in result.members] == ["minion", "minion", "minion", "minion", "minion"]
    assert result.total_power == 100


def test_group_assembler_can_repeat_member_templates_to_fill_budget() -> None:
    members = [
        _monster("cub", 20, gear_score=169, organization_type="pack"),
        _monster("veteran", 50, role="veteran", gear_score=600, organization_type="pack"),
    ]

    result = MonsterGroupAssembler(rng=random.Random(1)).assemble(members, budget=506, tier=1, danger=0.0)

    assert [member.variant_key for member in result.members] == ["cub", "cub"]
    assert result.total_power == 338


def test_group_assembler_randomizes_same_role_candidates() -> None:
    members = [
        _monster("cub_a", 20, gear_score=50, organization_type="swarm"),
        _monster("cub_b", 20, gear_score=50, organization_type="swarm"),
        _monster("cub_c", 20, gear_score=50, organization_type="swarm"),
    ]

    first = MonsterGroupAssembler(rng=random.Random(1)).assemble(members, budget=150, tier=1, danger=0.0)
    second = MonsterGroupAssembler(rng=random.Random(5)).assemble(members, budget=150, tier=1, danger=0.0)

    assert [member.variant_key for member in first.members] != [member.variant_key for member in second.members]
