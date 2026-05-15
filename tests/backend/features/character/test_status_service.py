from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.character.integrations import CharacterStateIntegrator
from src.backend.features.character.services.status_service import CharacterStatusService
from src.shared.enums.skill_enums import SkillProgressState


class FakeCharacterRepository:
    character = SimpleNamespace(
        character_id=7,
        user_id=uuid4(),
        name="Ada",
        gender="female",
        avatar_url="/avatar.png",
        created_at=datetime.now(UTC),
        location_id="52_52",
        attributes=None,
        skill_progress=[],
        symbiote=None,
    )

    def __init__(self, db_session):
        self.db_session = db_session

    async def get_by_id_and_user_id(self, char_id, user_id):
        return self.character


class MissingCharacterRepository(FakeCharacterRepository):
    async def get_by_id_and_user_id(self, char_id, user_id):
        return None


class RewardedCharacterRepository(FakeCharacterRepository):
    character = SimpleNamespace(
        character_id=7,
        user_id=uuid4(),
        name="Ada",
        gender="female",
        avatar_url="/avatar.png",
        created_at=datetime.now(UTC),
        location_id="52_52",
        attributes=SimpleNamespace(
            strength=10,
            agility=17,
            endurance=15,
            intellect=14,
            memory=9,
            mental=12,
            perception=11,
            projection=16,
            prediction=13,
        ),
        skill_progress=[
            SimpleNamespace(
                skill_key="skill_macing",
                total_xp=0.0,
                is_unlocked=True,
                progress_state=SkillProgressState.PLUS,
            ),
            SimpleNamespace(
                skill_key="locked_skill",
                total_xp=0.0,
                is_unlocked=False,
                progress_state=SkillProgressState.PAUSE,
            ),
        ],
        symbiote=SimpleNamespace(symbiote_name="SYSTEM", gift_rank=1),
    )


class FakeCharacterSessions:
    def __init__(self, document=None):
        self.document = document
        self.updated = None
        self.created = None

    def build_key(self, char_id):
        return f"game:ac:{char_id}"

    async def get_session(self, char_id):
        return self.document

    async def update_session(self, char_id, document):
        self.updated = document
        self.document = document

    async def create_session(self, char_id, document):
        self.created = document
        self.document = document


class FakeSkillRepository:
    pass


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
        placement = SimpleNamespace(storage_type="equipped", slot="main_hand")
        return [(instance, placement)]


class FakeGearScoreCalculator:
    def calculate_from_active_character(self, active_character):
        assert active_character["items"]["layout"]["equipment"]["main_hand"] == "item-weapon"
        return 777


def build_service(repo_cls, sessions):
    return CharacterStatusService(
        state_integrator=CharacterStateIntegrator(
            character_sessions=sessions,
            character_repo=repo_cls(object()),
            skill_repo=FakeSkillRepository(),
        )
    )


def build_actor_core_document():
    return {
        "schema_version": 1,
        "char_id": 7,
        "user_id": uuid4(),
        "state": "exploration",
        "prev_state": "scenario",
        "bio": {"name": "Ada", "gender": "female", "avatar": "/avatar.png", "created_at": datetime.now(UTC)},
        "location": {"current": "52_52"},
        "vitals": {"hp": {"cur": 100, "max": 100}},
        "attributes": {"strength": 8},
        "sessions": {"scenario_id": None, "combat_id": None, "inventory_id": None},
        "active_quest": None,
        "metrics": {"gear_score": 612},
        "skills": {"skill_macing": {"xp": 0.0}, "skill_medium_armor": {"xp": 0.0}},
        "symbiote": {"name": "SYSTEM"},
        "updated_at": datetime.now(UTC),
    }


def build_session_document():
    document = build_actor_core_document()
    document["bio"] = {"name": "Ada", "gender": "female", "avatar": "/avatar.png", "created_at": datetime.now(UTC)}
    document["vitals"] = {
        "hp": {"cur": 50, "max": 100, "regen": 10},
        "energy": {"cur": 20, "max": 100, "regen": 10},
        "stamina": {"cur": 10, "max": 100, "regen": 10},
        "last_update": datetime.now(UTC).timestamp() - 3,
    }
    document["attributes"] = {
        "strength": 8,
        "agility": 8,
        "endurance": 8,
        "intellect": 8,
        "memory": 8,
        "mental": 8,
        "perception": 8,
        "projection": 8,
        "prediction": 8,
    }
    return document


def build_legacy_session_document():
    document = build_session_document()
    document["attributes"] = {
        "strength": 8,
        "agility": 8,
        "endurance": 8,
        "intelligence": 8,
        "wisdom": 8,
        "men": 8,
        "perception": 8,
        "charisma": 8,
        "luck": 8,
    }
    return document


@pytest.mark.asyncio
async def test_get_actor_core_returns_game_ac_document():
    service = build_service(FakeCharacterRepository, FakeCharacterSessions(build_actor_core_document()))

    dto = await service.get_actor_core(SimpleNamespace(id=uuid4()), 7)

    assert dto.key == "game:ac:7"
    assert dto.char_id == 7
    assert dto.state == "exploration"
    assert dto.location["current"] == "52_52"
    assert dto.skills["skill_macing"]["xp"] == 0.0
    assert dto.panel is not None
    assert dto.panel.id == "character_status"
    avatar_widget = next(widget for widget in dto.panel.widgets if widget.title == "PROFILE")
    assert avatar_widget.data["gear_score"] == 612
    attributes_widget = next(widget for widget in dto.panel.widgets if widget.title == "ATTRIBUTES")
    assert attributes_widget.type == "attribute_grid"
    assert [group["title"] for group in attributes_widget.data["groups"]] == ["BODY", "CORE", "SENSOR"]
    skills_widget = next(widget for widget in dto.panel.widgets if widget.title == "SKILLS")
    assert skills_widget.type == "skill_groups"
    assert [group["title"] for group in skills_widget.data["groups"]] == ["WEAPON MASTERY", "ARMOR"]
    assert skills_widget.data["groups"][0]["items"][0]["catalog_key"] == "skill_macing"
    assert skills_widget.data["groups"][0]["items"][0]["value"] == "0%"


@pytest.mark.asyncio
async def test_get_actor_core_formats_skill_values_as_percentages():
    document = build_actor_core_document()
    document["skills"] = {
        "skill_macing": {"xp": 0.0352},
        "skill_medium_armor": {"xp": 1.0},
    }
    service = build_service(FakeCharacterRepository, FakeCharacterSessions(document))

    dto = await service.get_actor_core(SimpleNamespace(id=uuid4()), 7)

    skills_widget = next(widget for widget in dto.panel.widgets if widget.title == "SKILLS")
    weapon_group = next(group for group in skills_widget.data["groups"] if group["title"] == "WEAPON MASTERY")
    armor_group = next(group for group in skills_widget.data["groups"] if group["title"] == "ARMOR")
    assert weapon_group["items"][0]["value"] == "3.5%"
    assert armor_group["items"][0]["value"] == "100%"


@pytest.mark.asyncio
async def test_get_actor_core_rejects_unowned_character():
    service = build_service(MissingCharacterRepository, FakeCharacterSessions(build_actor_core_document()))

    with pytest.raises(BusinessLogicException):
        await service.get_actor_core(SimpleNamespace(id=uuid4()), 7)


@pytest.mark.asyncio
async def test_get_actor_core_initializes_missing_actor_core():
    sessions = FakeCharacterSessions(None)
    service = build_service(FakeCharacterRepository, sessions)

    dto = await service.get_actor_core(SimpleNamespace(id=uuid4()), 7)

    assert dto.key == "game:ac:7"
    assert dto.char_id == 7
    assert dto.bio["name"] == "Ada"
    assert dto.location["current"] == "52_52"
    assert sessions.created is not None
    assert sessions.created["symbiote"]["name"] == "SYSTEM"


@pytest.mark.asyncio
async def test_get_actor_core_initializes_items_and_gear_score_from_inventory():
    sessions = FakeCharacterSessions(None)
    service = CharacterStatusService(
        state_integrator=CharacterStateIntegrator(
            character_sessions=sessions,
            character_repo=FakeCharacterRepository(object()),
            skill_repo=FakeSkillRepository(),
            inventory_repo=FakeInventoryRepository(),
            gear_score_calculator=FakeGearScoreCalculator(),
        )
    )

    dto = await service.get_actor_core(SimpleNamespace(id=uuid4()), 7)

    assert sessions.created["items"]["layout"]["equipment"]["main_hand"] == "item-weapon"
    assert dto.metrics["gear_score"] == 777
    avatar_widget = next(widget for widget in dto.panel.widgets if widget.title == "PROFILE")
    assert avatar_widget.data["gear_score"] == 777


@pytest.mark.asyncio
async def test_get_actor_core_initializes_actor_core_from_persisted_actor_state():
    sessions = FakeCharacterSessions(None)
    service = build_service(RewardedCharacterRepository, sessions)

    dto = await service.get_actor_core(SimpleNamespace(id=uuid4()), 7)

    assert dto.attributes["agility"] == 17
    assert dto.attributes["projection"] == 16
    assert dto.vitals["hp"]["max"] == 60
    assert dto.vitals["hp"]["cur"] == 60
    assert dto.vitals["energy"]["max"] == 24
    assert dto.vitals["stamina"]["max"] == 150
    assert dto.skills["skill_macing"]["state"] == "PLUS"
    assert "locked_skill" not in dto.skills
    assert sessions.created["attributes"]["agility"] == 17
    assert sessions.created["vitals"]["hp"]["max"] == 60
    assert sessions.created["skills"]["skill_macing"]["unlocked"] is True


@pytest.mark.asyncio
async def test_get_actor_core_repairs_stale_default_actor_core_from_persisted_actor_state():
    document = build_session_document()
    document["skills"] = {}
    sessions = FakeCharacterSessions(document)
    service = build_service(RewardedCharacterRepository, sessions)

    dto = await service.get_actor_core(SimpleNamespace(id=uuid4()), 7)

    assert dto.attributes["agility"] == 17
    assert dto.attributes["projection"] == 16
    assert dto.vitals["hp"]["max"] == 60
    assert dto.vitals["hp"]["cur"] == 60
    assert dto.vitals["energy"]["max"] == 24
    assert dto.skills["skill_macing"]["state"] == "PLUS"
    assert sessions.updated is not None
    assert sessions.updated["attributes"]["agility"] == 17
    assert sessions.updated["vitals"]["hp"]["cur"] == 60
    assert sessions.updated["vitals"]["hp"]["max"] == 60
    assert sessions.updated["skills"]["skill_macing"]["unlocked"] is True


@pytest.mark.asyncio
async def test_get_actor_core_rebuilds_invalid_legacy_attribute_session_to_new_contract():
    sessions = FakeCharacterSessions(build_legacy_session_document())
    service = build_service(RewardedCharacterRepository, sessions)

    dto = await service.get_actor_core(SimpleNamespace(id=uuid4()), 7)

    assert dto.attributes["intellect"] == 14
    assert dto.attributes["projection"] == 16
    assert sessions.updated is not None
    assert "intelligence" not in sessions.updated["attributes"]
    assert "charisma" not in sessions.updated["attributes"]
    assert sessions.updated["attributes"]["intellect"] == 14


@pytest.mark.asyncio
async def test_get_actor_core_keeps_runtime_attributes_when_not_default():
    document = build_session_document()
    document["attributes"]["agility"] = 21
    sessions = FakeCharacterSessions(document)
    service = build_service(RewardedCharacterRepository, sessions)

    dto = await service.get_actor_core(SimpleNamespace(id=uuid4()), 7)

    assert dto.attributes["agility"] == 21
    assert dto.vitals["hp"]["cur"] == 32
    assert dto.vitals["hp"]["max"] == 32


@pytest.mark.asyncio
async def test_get_status_returns_flat_regenerated_vitals():
    sessions = FakeCharacterSessions(build_session_document())
    service = build_service(FakeCharacterRepository, sessions)

    status = await service.get_status(SimpleNamespace(id=uuid4()), 7)

    assert status.character_id == 7
    assert status.hp == 32
    assert status.max_hp == 32
    assert status.avatar_url == "/avatar.png"
    assert sessions.updated is not None


@pytest.mark.asyncio
async def test_get_status_rejects_unowned_character():
    service = build_service(MissingCharacterRepository, FakeCharacterSessions(build_session_document()))

    with pytest.raises(BusinessLogicException):
        await service.get_status(SimpleNamespace(id=uuid4()), 7)
