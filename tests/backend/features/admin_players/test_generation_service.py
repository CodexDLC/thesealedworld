from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from src.backend.features.admin_players.dto import AdminPlayerGenerateCharacterRequestDTO
from src.backend.features.admin_players.generation_service import AdminPlayerCharacterGenerationService


class FakeCharacterRepository:
    def __init__(self) -> None:
        self.character = None
        self.committed = False

    async def count_by_user_id(self, user_id: UUID) -> int:
        return 0

    async def exists_by_name_key(self, name_key: str) -> bool:
        return False

    async def create_with_defaults(self, **kwargs):
        now = datetime(2026, 5, 24, tzinfo=UTC)
        self.character = SimpleNamespace(
            character_id=123,
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        return self.character

    async def commit(self) -> None:
        self.committed = True


class FakeAttributesRepository:
    def __init__(self) -> None:
        self.rows = []

    async def upsert_attributes(self, char_id: int, attributes: dict[str, int]) -> None:
        self.rows.append((char_id, attributes))


class FakeSkillRepository:
    def __init__(self) -> None:
        self.calls = []

    async def unlock_skills(self, char_id: int, skill_keys: list[str], **kwargs) -> None:
        self.calls.append((char_id, skill_keys, kwargs))


class FakeProgressionRepository:
    def __init__(self) -> None:
        self.calls = []

    async def set_free_xp(self, char_id: int, value: float) -> None:
        self.calls.append((char_id, value))


class FakeItemGeneration:
    def __init__(self) -> None:
        self.requests = []

    async def generate_mechanical(self, request):
        self.requests.append(request)
        return SimpleNamespace(item_ids=[f"item-{len(self.requests)}"])


class FakeMonsterRepository:
    def __init__(self) -> None:
        self.clan_id = uuid4()

    async def get_generated_clan(self, clan_id: str):
        assert clan_id == str(self.clan_id)
        return _source_clan(self.clan_id)

    async def list_generated_clans(self, limit: int = 100):
        return [_source_clan(self.clan_id)]


@pytest.mark.unit
async def test_admin_generation_service_creates_character_skills_and_family_equipment() -> None:
    character_repo = FakeCharacterRepository()
    attributes_repo = FakeAttributesRepository()
    skill_repo = FakeSkillRepository()
    progression_repo = FakeProgressionRepository()
    item_generation = FakeItemGeneration()
    monster_repo = FakeMonsterRepository()
    service = AdminPlayerCharacterGenerationService(
        character_repo=character_repo,
        attributes_repo=attributes_repo,
        skill_repo=skill_repo,
        progression_repo=progression_repo,
        item_generation=item_generation,
        monster_repo=monster_repo,
    )

    result = await service.generate_for_user(
        UUID("11111111-1111-1111-1111-111111111111"),
        AdminPlayerGenerateCharacterRequestDTO(
            slot_index=2,
            name="Test_Admin_Hero",
            skill_progress_percent=75,
            item_tier=2,
            source_clan_id=str(monster_repo.clan_id),
        ),
    )

    assert result.character.character_id == 123
    assert result.family_id == "bandit_gang"
    assert result.source_clan_id == str(monster_repo.clan_id)
    assert result.item_tier == 2
    assert character_repo.committed is True
    assert attributes_repo.rows[0][0] == 123
    assert sum(attributes_repo.rows[0][1].values()) == 81
    assert skill_repo.calls[0][2]["initial_xp"] == 0.75
    assert item_generation.requests
    assert all(request.placement_ref.storage_type == "equipped" for request in item_generation.requests)
    assert item_generation.requests[0].source_context["family_id"] == "bandit_gang"
    assert item_generation.requests[0].source_context["source_clan_id"] == str(monster_repo.clan_id)


@pytest.mark.unit
async def test_admin_generation_options_expose_only_generated_humanoid_equipment_clans() -> None:
    monster_repo = FakeMonsterRepository()
    service = AdminPlayerCharacterGenerationService(
        character_repo=FakeCharacterRepository(),
        attributes_repo=FakeAttributesRepository(),
        skill_repo=FakeSkillRepository(),
        progression_repo=FakeProgressionRepository(),
        item_generation=FakeItemGeneration(),
        monster_repo=monster_repo,
    )

    options = await service.list_generation_options()

    assert [option.clan_id for option in options.clans] == [str(monster_repo.clan_id)]
    assert options.clans[0].label == "Rust Cross / 50_52"


def _source_clan(clan_id):
    return SimpleNamespace(
        id=clan_id,
        family_id="bandit_gang",
        tier=2,
        zone_id="50_52",
        unique_hash="unique",
        name_ru="Rust Cross",
        source_context={"source": "test"},
        members=[
            SimpleNamespace(variant_key="bandit_raider", role="veteran", member_tier=2),
        ],
    )
