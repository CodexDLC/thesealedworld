from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.backend.features.character.integrations import CharacterStateIntegrator
from src.shared.enums.skill_enums import SkillProgressState


class FakeCharacterSessions:
    def __init__(self) -> None:
        self.replaced: dict | None = None

    async def replace_session(self, char_id, document):
        self.replaced = document


class FakeCharacterRepository:
    def __init__(self, character) -> None:
        self.character = character

    async def get_by_id_and_user_id(self, char_id, user_id):
        return self.character


class FakeSkillRepository:
    pass


class FakeProgressionRepository:
    async def get_by_character_id(self, char_id):
        return SimpleNamespace(free_xp=12.5)


class FakeInventoryRepository:
    async def list_character_items(self, char_id, *, expedition_run_id=None):
        instance = SimpleNamespace(
            id="item-weapon",
            base_id="sword",
            item_type="weapon",
            mechanics={"slot": "main_hand", "valid_slots": ["main_hand"], "power": 10},
            metadata_={},
            appearance={},
            name="Practice Sword",
            description="Starter blade",
            rarity="common",
            rarity_tier=1,
            generation={},
        )
        placement = SimpleNamespace(holder_type="character", storage_type="equipped", slot="main_hand")
        return [(instance, placement)]


class FakeExpeditionRepository:
    async def get_active_for_character(self, char_id):
        return SimpleNamespace(
            status="active",
            current_location_id="60_61",
            run_id="expedition-run-1",
            corpse_id=None,
            pending_progress_json={
                "free_xp": 2.5,
                "skills": {"skill_swords": 0.4},
                "weapon": {"main_hand": 1.0},
                "armor": {"chest": 0.3},
                "symbiote": {"gift": 0.2},
            },
        )


class FakeGearScoreCalculator:
    def calculate_from_active_character(self, active_character):
        assert active_character["items"]["layout"]["equipment"]["main_hand"] == "item-weapon"
        return 777


@pytest.mark.asyncio
async def test_bootstrap_active_session_restores_persisted_runtime_refs_progress_and_items() -> None:
    user_id = uuid4()
    scenario_id = "8c550fc2-a99c-4759-aaa6-ebed9a343f8b"
    character = SimpleNamespace(
        character_id=7,
        user_id=user_id,
        name="Ada",
        gender="female",
        avatar_url="/avatar.png",
        created_at=datetime.now(UTC),
        game_stage="scenario",
        prev_game_stage="lobby",
        location_id="52_58",
        prev_location_id="52_52",
        vitals_snapshot={
            "hp": {"cur": 90, "max": 100, "regen": 1},
            "energy": {"cur": 80, "max": 100, "regen": 1},
            "stamina": {"cur": 70, "max": 100, "regen": 1},
            "last_update": 0.0,
        },
        active_sessions={
            "scenario_id": scenario_id,
            "combat_id": None,
            "combat_finalization_id": None,
            "encounter_id": None,
            "arena_id": None,
            "inventory_id": "inventory-window-1",
            "death_run_id": None,
            "death_corpse_id": None,
            "active_quest": "awakening_rift",
        },
        attributes=SimpleNamespace(
            strength=17,
            agility=16,
            endurance=15,
            intellect=14,
            memory=13,
            mental=12,
            perception=11,
            projection=10,
            prediction=9,
        ),
        skill_progress=[
            SimpleNamespace(
                skill_key="skill_swords",
                total_xp=0.25,
                is_unlocked=True,
                progress_state=SkillProgressState.PLUS,
            ),
            SimpleNamespace(
                skill_key="locked_skill",
                total_xp=0.75,
                is_unlocked=False,
                progress_state=SkillProgressState.PAUSE,
            ),
        ],
        symbiote=SimpleNamespace(symbiote_name="SYSTEM", gift_id="gift-flame", gift_xp=42, gift_rank=1),
    )
    sessions = FakeCharacterSessions()
    integrator = CharacterStateIntegrator(
        character_sessions=sessions,
        character_repo=FakeCharacterRepository(character),
        skill_repo=FakeSkillRepository(),
        progression_repo=FakeProgressionRepository(),
        inventory_repo=FakeInventoryRepository(),
        gear_score_calculator=FakeGearScoreCalculator(),
    )

    session_doc = await integrator.bootstrap_active_session(user_id, 7)

    assert session_doc.state == "scenario"
    assert session_doc.prev_state == "lobby"
    assert session_doc.location.current == "52_58"
    assert session_doc.location.prev == "52_52"
    assert session_doc.sessions.scenario_id == scenario_id
    assert session_doc.sessions.inventory_id == "inventory-window-1"
    assert session_doc.active_quest == "awakening_rift"
    assert session_doc.vitals.hp.cur == 64
    assert session_doc.vitals.hp.max == 64
    assert session_doc.vitals.energy.cur == 39
    assert session_doc.vitals.energy.max == 39
    assert session_doc.vitals.stamina.cur == 50
    assert session_doc.vitals.stamina.max == 50
    assert session_doc.attributes.strength == 17
    assert session_doc.skills["skill_swords"]["xp"] == 0.25
    assert "locked_skill" not in session_doc.skills
    assert session_doc.progression.free_xp == 12.5
    assert session_doc.symbiote.gift_id == "gift-flame"
    assert session_doc.symbiote.gift_xp == 42
    assert session_doc.items.layout.equipment["main_hand"] == "item-weapon"
    assert session_doc.metrics.gear_score == 777

    assert sessions.replaced is not None
    assert sessions.replaced["state"] == "scenario"
    assert sessions.replaced["sessions"]["scenario_id"] == scenario_id
    assert sessions.replaced["active_quest"] == "awakening_rift"
    assert sessions.replaced["skills"]["skill_swords"]["xp"] == 0.25
    assert sessions.replaced["progression"]["free_xp"] == 12.5
    assert sessions.replaced["symbiote"]["gift_id"] == "gift-flame"
    assert sessions.replaced["symbiote"]["gift_xp"] == 42
    assert sessions.replaced["items"]["layout"]["equipment"]["main_hand"] == "item-weapon"


@pytest.mark.asyncio
async def test_bootstrap_active_session_restores_active_expedition_pending_progress_and_risk() -> None:
    user_id = uuid4()
    character = SimpleNamespace(
        character_id=8,
        user_id=user_id,
        name="Rook",
        gender="male",
        avatar_url=None,
        created_at=datetime.now(UTC),
        game_stage="exploration",
        prev_game_stage="scenario",
        location_id="52_58",
        prev_location_id="52_52",
        vitals_snapshot=None,
        active_sessions={},
        attributes=SimpleNamespace(
            strength=8,
            agility=8,
            endurance=8,
            intellect=8,
            memory=8,
            mental=8,
            perception=8,
            projection=8,
            prediction=8,
        ),
        skill_progress=[],
        symbiote=None,
    )
    sessions = FakeCharacterSessions()
    integrator = CharacterStateIntegrator(
        character_sessions=sessions,
        character_repo=FakeCharacterRepository(character),
        skill_repo=FakeSkillRepository(),
        expedition_repo=FakeExpeditionRepository(),
    )

    session_doc = await integrator.bootstrap_active_session(user_id, 8)

    assert session_doc.state == "exploration"
    assert session_doc.prev_state == "scenario"
    assert session_doc.location.current == "60_61"
    assert session_doc.pending_progress.free_xp == 2.5
    assert session_doc.pending_progress.skills["skill_swords"] == 0.4
    assert session_doc.pending_progress.weapon["main_hand"] == 1.0
    assert session_doc.risk.sync_state == "unsafe"
    assert session_doc.risk.system_connect is False
    assert session_doc.risk.run_id == "expedition-run-1"
    assert session_doc.risk.pending_free_xp == 2.5
    assert session_doc.risk.pending_skill_count == 1

    assert sessions.replaced is not None
    assert sessions.replaced["location"]["current"] == "60_61"
    assert sessions.replaced["pending_progress"]["skills"]["skill_swords"] == 0.4
    assert sessions.replaced["risk"]["run_id"] == "expedition-run-1"
