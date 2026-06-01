from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.backend.features.game_lobby.integrations import CreatedLobbyCharacter, GameLobbyIntegration
from src.shared.enums import CoreDomain
from src.shared.enums.skill_enums import SkillProgressState


class FakeCharacterRepository:
    def __init__(self, character=None) -> None:
        self.committed = False
        self.character = character
        self.session = SimpleNamespace(expire_all=lambda: None)

    async def get_by_id_and_user_id(self, character_id, user_id):
        if self.character is None:
            return None
        if self.character.character_id == character_id and self.character.user_id == user_id:
            return self.character
        return None

    async def commit(self) -> None:
        self.committed = True


class FakeAttributesRepository:
    def __init__(self) -> None:
        self.attributes: dict[int, dict[str, int]] = {}

    async def upsert_attributes(self, char_id: int, attributes: dict[str, int]) -> None:
        self.attributes[char_id] = dict(attributes)


class FakeSkillRepository:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.deleted: list[int] = []

    async def upsert_progress_rows(self, rows: list[dict]) -> None:
        self.rows.extend(rows)

    async def delete_by_character_id(self, char_id: int) -> None:
        self.deleted.append(char_id)


class FakeProgressionRepository:
    def __init__(self) -> None:
        self.free_xp: dict[int, float] = {}

    async def set_free_xp(self, char_id: int, value: float) -> None:
        self.free_xp[char_id] = float(value)


class FakeItemPersistence:
    def __init__(self) -> None:
        self.created: list[tuple[str, str, str]] = []
        self.transferred: list[int] = []

    async def get_text_visual_template_by_hash(self, text_visual_hash: str):
        return None

    async def create_text_visual_template(self, item, **kwargs):
        return SimpleNamespace(id=f"tpl-{item.base_id}", name=item.name, description=item.description)

    async def create_mechanical_item(self, item, placement_ref, **kwargs) -> str:
        item_id = f"item-{len(self.created) + 1}"
        self.created.append((item.base_id, placement_ref.storage_type, placement_ref.slot))
        return item_id

    async def transfer_deleted_character_items_to_system(self, character_id: int) -> int:
        self.transferred.append(character_id)
        return 3


class FakeCharacterSessions:
    def __init__(self) -> None:
        self.deleted: list[int] = []

    async def delete_session(self, char_id: int) -> None:
        self.deleted.append(char_id)


class FakeInventorySessions:
    def __init__(self) -> None:
        self.deleted: list[int] = []

    async def delete(self, char_id: int) -> None:
        self.deleted.append(char_id)


class FakeStartingImprintDistribution:
    def __init__(self, selected: str) -> None:
        self.selected = selected
        self.calls: list[dict[str, object]] = []

    async def select_and_record(self, *, user_id, seed, imprint_keys):
        self.calls.append({"user_id": user_id, "seed": seed, "imprint_keys": tuple(imprint_keys)})
        return self.selected


@pytest.mark.asyncio
async def test_materialize_starting_imprint_persists_attributes_skills_and_equipped_items() -> None:
    character = CreatedLobbyCharacter(
        character_id=7,
        user_id=uuid4(),
        name="Nea",
        gender="female",
        avatar_url="/avatar.png",
        created_at=datetime.now(UTC),
        location_id="52_52",
    )
    character_repo = FakeCharacterRepository()
    attributes_repo = FakeAttributesRepository()
    skill_repo = FakeSkillRepository()
    progression_repo = FakeProgressionRepository()
    item_persistence = FakeItemPersistence()
    integration = GameLobbyIntegration(
        character_repo=character_repo,
        attributes_repo=attributes_repo,
        skill_repo=skill_repo,
        progression_repo=progression_repo,
        item_persistence=item_persistence,
        character_sessions=SimpleNamespace(),
    )

    result = await integration.materialize_starting_imprint(
        character,
        imprint_key="starter_guard_01",
        seed="test-seed",
    )

    assert result["imprint_key"] == "starter_guard_01"
    assert attributes_repo.attributes[7]["strength"] == 17
    assert attributes_repo.attributes[7]["agility"] == 14
    assert attributes_repo.attributes[7]["endurance"] == 16
    assert attributes_repo.attributes[7]["perception"] == 15
    assert progression_repo.free_xp[7] == 0.0
    assert {row["skill_key"]: row["total_xp"] for row in skill_repo.rows} == {
        "skill_swords": 0.20,
        "skill_shield_mastery": 0.15,
        "skill_medium_armor": 0.10,
    }
    assert all(row["progress_state"] == SkillProgressState.PLUS for row in skill_repo.rows)
    assert ("sword", "equipped", "main_hand") in item_persistence.created
    assert ("shield", "equipped", "off_hand") in item_persistence.created
    assert ("jerkin", "equipped", "chest_armor") in item_persistence.created
    assert result["item_ids"] == [f"item-{index}" for index in range(1, len(item_persistence.created) + 1)]
    assert character_repo.committed is True


@pytest.mark.asyncio
async def test_materialize_starting_imprint_places_second_fencing_weapon_offhand() -> None:
    character = CreatedLobbyCharacter(
        character_id=7,
        user_id=uuid4(),
        name="Nea",
        gender="female",
        avatar_url="/avatar.png",
        created_at=datetime.now(UTC),
        location_id="52_52",
    )
    item_persistence = FakeItemPersistence()
    integration = GameLobbyIntegration(
        character_repo=FakeCharacterRepository(),
        attributes_repo=FakeAttributesRepository(),
        skill_repo=FakeSkillRepository(),
        progression_repo=FakeProgressionRepository(),
        item_persistence=item_persistence,
        character_sessions=SimpleNamespace(),
    )

    await integration.materialize_starting_imprint(
        character,
        imprint_key="starter_dual_blades_01",
        seed="test-seed",
    )

    assert ("stiletto", "equipped", "main_hand") in item_persistence.created
    assert ("stiletto", "equipped", "off_hand") in item_persistence.created


@pytest.mark.asyncio
async def test_materialize_starting_imprint_uses_distribution_for_automatic_selection() -> None:
    user_id = uuid4()
    character = CreatedLobbyCharacter(
        character_id=7,
        user_id=user_id,
        name="Nea",
        gender="female",
        avatar_url="/avatar.png",
        created_at=datetime.now(UTC),
        location_id="52_52",
    )
    character_repo = FakeCharacterRepository()
    attributes_repo = FakeAttributesRepository()
    skill_repo = FakeSkillRepository()
    distribution = FakeStartingImprintDistribution("starter_staff_01")
    integration = GameLobbyIntegration(
        character_repo=character_repo,
        attributes_repo=attributes_repo,
        skill_repo=skill_repo,
        item_persistence=FakeItemPersistence(),
        character_sessions=SimpleNamespace(),
        starting_imprint_distribution=distribution,
    )

    result = await integration.materialize_starting_imprint(character, seed="creation-seed")

    assert result["imprint_key"] == "starter_staff_01"
    assert result["skill_keys"] == [
        "skill_polearms",
        "skill_two_handed",
        "skill_medium_armor",
    ]
    assert distribution.calls == [
        {
            "user_id": user_id,
            "seed": "creation-seed",
            "imprint_keys": (
                "starter_guard_01",
                "starter_breaker_01",
                "starter_dual_blades_01",
                "starter_dual_sword_01",
                "starter_dual_mace_01",
                "starter_pathfinder_01",
                "starter_staff_01",
                "starter_heavy_guard_01",
                "starter_tactician_01",
                "starter_rift_survivor_01",
            ),
        }
    ]


@pytest.mark.asyncio
async def test_materialize_starting_imprint_does_not_record_distribution_for_explicit_key() -> None:
    character = CreatedLobbyCharacter(
        character_id=7,
        user_id=uuid4(),
        name="Nea",
        gender="female",
        avatar_url="/avatar.png",
        created_at=datetime.now(UTC),
        location_id="52_52",
    )
    distribution = FakeStartingImprintDistribution("starter_staff_01")
    integration = GameLobbyIntegration(
        character_repo=FakeCharacterRepository(),
        attributes_repo=FakeAttributesRepository(),
        skill_repo=FakeSkillRepository(),
        item_persistence=FakeItemPersistence(),
        character_sessions=SimpleNamespace(),
        starting_imprint_distribution=distribution,
    )

    result = await integration.materialize_starting_imprint(
        character,
        imprint_key="starter_guard_01",
        seed="creation-seed",
    )

    assert result["imprint_key"] == "starter_guard_01"
    assert distribution.calls == []


@pytest.mark.asyncio
async def test_reset_character_to_starting_imprint_clears_old_runtime_and_rematerializes_identity() -> None:
    user_id = uuid4()
    character = SimpleNamespace(
        character_id=7,
        user_id=user_id,
        name="Nea",
        gender="female",
        avatar_url="/avatar.png",
        created_at=datetime.now(UTC),
        location_id="52_52",
        prev_location_id="51_51",
        vitals_snapshot={"hp": {"cur": 0, "max": 120}},
        game_stage=CoreDomain.DEATH.value,
        prev_game_stage=CoreDomain.COMBAT.value,
        active_sessions={"death_run_id": "run-1", "rift_session_id": "rift-run-1"},
        respawn_anchor_location_id="51_51",
    )
    character_repo = FakeCharacterRepository(character=character)
    attributes_repo = FakeAttributesRepository()
    skill_repo = FakeSkillRepository()
    progression_repo = FakeProgressionRepository()
    item_persistence = FakeItemPersistence()
    character_sessions = FakeCharacterSessions()
    inventory_sessions = FakeInventorySessions()
    integration = GameLobbyIntegration(
        character_repo=character_repo,
        attributes_repo=attributes_repo,
        skill_repo=skill_repo,
        progression_repo=progression_repo,
        item_persistence=item_persistence,
        inventory_sessions=inventory_sessions,
        character_sessions=character_sessions,
    )
    integration.create_active_session = AsyncMock()
    integration.bootstrap_active_character = AsyncMock()

    result = await integration.reset_character_to_starting_imprint(
        user_id=user_id,
        character_id=7,
        seed="reset-seed",
        imprint_key="starter_guard_01",
    )

    assert result["status"] == "reset"
    assert result["starting_imprint"]["imprint_key"] == "starter_guard_01"
    assert attributes_repo.attributes[7]["strength"] == 17
    assert attributes_repo.attributes[7]["agility"] == 14
    assert attributes_repo.attributes[7]["endurance"] == 16
    assert attributes_repo.attributes[7]["perception"] == 15
    assert progression_repo.free_xp[7] == 0.0
    assert skill_repo.deleted == [7]
    assert item_persistence.transferred == [7]
    assert character_sessions.deleted == [7]
    assert inventory_sessions.deleted == [7]
    integration.create_active_session.assert_not_awaited()
    integration.bootstrap_active_character.assert_awaited_once_with(user_id=user_id, character_id=7)
    assert integration.bootstrap_active_character.await_args.kwargs == {"user_id": user_id, "character_id": 7}
    assert character.avatar_url == "/static/images/avatars/silhouette_f.webp"
    assert character.game_stage == CoreDomain.EXPLORATION.value
    assert character.prev_game_stage == CoreDomain.DEATH.value
    assert character.location_id == "52_52"
    assert character.prev_location_id is None
    assert character.vitals_snapshot is None
    assert character.active_sessions == {}
    assert character.respawn_anchor_location_id == "52_52"
