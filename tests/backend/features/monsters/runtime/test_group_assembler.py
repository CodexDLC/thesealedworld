import uuid

from src.backend.features.monsters.dto.generation import GeneratedMonster
from src.backend.features.monsters.runtime.group_assembler import MonsterGroupAssembler


def _monster(variant_key: str, threat: int) -> GeneratedMonster:
    return GeneratedMonster(
        id=uuid.uuid4(),
        clan_id=uuid.uuid4(),
        variant_key=variant_key,
        role="minion",
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
    )


def test_group_assembler_selects_subset_closest_to_budget() -> None:
    members = [_monster("a", 20), _monster("b", 20), _monster("c", 50), _monster("d", 150)]

    result = MonsterGroupAssembler().assemble(members, budget=90, tier=1, danger=0.0)

    assert [member.variant_key for member in result.members] == ["a", "b", "c"]
    assert result.total_power == 90
    assert result.adjusted_budget == 90


def test_group_assembler_applies_danger_budget_bonus() -> None:
    members = [_monster("a", 20), _monster("b", 50), _monster("c", 150)]

    result = MonsterGroupAssembler().assemble(members, budget=120, tier=1, danger=1.0)

    assert result.adjusted_budget == 150
    assert [member.variant_key for member in result.members] == ["c"]
