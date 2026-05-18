from __future__ import annotations

import pytest

from src.backend.features.exploration.gateway import ExplorationGateway
from src.backend.features.exploration.services.encounter_service import ExplorationEncounterService
from src.backend.features.exploration.services.encounter_session_service import ExplorationEncounterSessionService
from src.backend.features.exploration.services.exploration_service import ExplorationService
from src.backend.features.exploration.services.navigation_service import ExplorationNavigationService
from src.shared.enums import CoreDomain
from src.shared.schemas.exploration import (
    DetectionStatus,
    EncounterDTO,
    EncounterOptionDTO,
    EncounterType,
    WorldNavigationDTO,
)


class FakeExplorationIntegrator:
    def __init__(self) -> None:
        self.loc_id = "52_51"
        self.locations = {
            "52_51": {
                "name": "Current",
                "description": "Current location",
                "exits": {"52_52": {}},
                "flags": {"threat_tier": 1},
            },
            "52_52": {
                "name": "Target",
                "description": "Target location",
                "exits": {},
                "flags": {"threat_tier": 1},
            },
        }
        self.moves: list[tuple[int, str | None, str]] = []
        self.world_themes: list[tuple[int, dict]] = []

    async def get_player_location_id(self, char_id: int) -> str:
        return self.loc_id

    async def get_location_data(self, loc_id: str) -> dict:
        return self.locations.get(loc_id, {})

    async def move_player(self, char_id: int, from_loc: str | None, to_loc: str) -> bool:
        self.moves.append((char_id, from_loc, to_loc))
        self.loc_id = to_loc
        return True

    async def get_actor_skills(self, char_id: int) -> dict[str, float]:
        return {"skill_pathfinder": 1.0, "skill_scouting": 1.0}

    async def get_players_count(self, loc_id: str, exclude_char_id: int | None = None) -> int:
        return 0

    async def get_battles(self, loc_id: str) -> dict[str, str]:
        return {}

    async def set_world_theme(self, char_id: int, world_theme: dict) -> None:
        self.world_themes.append((char_id, world_theme))


class FakeEncounterIntegration:
    def __init__(self, *, active_id: str | None = None, sessions: dict[str, dict] | None = None) -> None:
        self.active_id = active_id
        self.sessions = sessions or {}
        self.created: list[tuple[str, dict]] = []
        self.attached: list[tuple[int, str]] = []
        self.combat_sessions: list[tuple[int, str]] = []
        self.detached: list[int] = []
        self.cleared: list[str] = []
        self.patched: list[tuple[str, dict]] = []
        self.progress: list[tuple[int, dict[str, float]]] = []

    async def get_ac_skill_snapshot(self, char_id: int) -> _SkillSnapshot:
        return _SkillSnapshot()

    async def get_ac_attribute_snapshot(self, char_id: int) -> dict[str, float]:
        return {
            "perception": 8.0,
            "memory": 8.0,
            "agility": 8.0,
            "endurance": 8.0,
        }

    async def apply_skill_progress(self, char_id: int, rewards: dict[str, float]) -> None:
        self.progress.append((char_id, rewards))

    async def get_active_encounter_id(self, char_id: int) -> str | None:
        return self.active_id

    async def attach_encounter_session(self, char_id: int, encounter_id: str) -> None:
        self.active_id = encounter_id
        self.attached.append((char_id, encounter_id))

    async def detach_encounter_session(self, char_id: int) -> None:
        self.active_id = None
        self.detached.append(char_id)

    async def create_encounter_session(self, encounter_id: str, payload: dict) -> dict:
        self.sessions[encounter_id] = dict(payload)
        self.created.append((encounter_id, dict(payload)))
        return self.sessions[encounter_id]

    async def get_encounter_session(self, encounter_id: str) -> dict | None:
        return self.sessions.get(encounter_id)

    async def patch_encounter_session(self, encounter_id: str, updates: dict) -> None:
        self.patched.append((encounter_id, updates))
        session = self.sessions.get(encounter_id)
        if session is not None:
            session.update(updates)

    async def clear_encounter_session(self, encounter_id: str) -> None:
        self.cleared.append(encounter_id)
        self.sessions.pop(encounter_id, None)

    async def attach_combat_session(self, char_id: int, combat_id: str) -> None:
        self.combat_sessions.append((char_id, combat_id))


class FakeEncounterEngine:
    def __init__(self, encounter: EncounterDTO | None = None) -> None:
        self.encounter = encounter
        self.calls: list[dict] = []

    async def try_generate_encounter(self, **kwargs):
        self.calls.append(kwargs)
        return self.encounter


def _encounter(encounter_id: str = "enc-1") -> EncounterDTO:
    return EncounterDTO(
        id=encounter_id,
        type=EncounterType.COMBAT,
        status=DetectionStatus.DETECTED,
        title="Threat",
        description="An active encounter",
        options=[EncounterOptionDTO(id="bypass", label="Bypass")],
    )


class _SkillSnapshot:
    skill_scouting = 0.0
    skill_pathfinder = 0.0
    skill_hunting = 0.0
    skill_taming = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "skill_scouting": self.skill_scouting,
            "skill_pathfinder": self.skill_pathfinder,
            "skill_hunting": self.skill_hunting,
            "skill_taming": self.skill_taming,
        }


def _ready_combat_encounter(encounter_id: str = "enc-1", combat_id: str = "combat-enc-1") -> EncounterDTO:
    encounter = _encounter(encounter_id)
    return encounter.model_copy(
        update={
            "session_id": combat_id,
            "metadata": {
                "combat": {
                    "status": "ready",
                    "combat_id": combat_id,
                    "request": {"combat_id": combat_id},
                    "response": {"status": "ready", "combat_id": combat_id},
                }
            },
        }
    )


@pytest.mark.asyncio
async def test_look_around_api_restores_active_encounter_payload() -> None:
    encounter = _encounter()
    encounter_integration = FakeEncounterIntegration(
        active_id="enc-1",
        sessions={"enc-1": {"payload": encounter.model_dump(mode="json")}},
    )
    navigation = ExplorationNavigationService(FakeExplorationIntegrator())  # type: ignore[arg-type]
    gateway = ExplorationGateway(
        navigation=navigation,
        encounters=ExplorationEncounterService(
            engine=FakeEncounterEngine(),  # type: ignore[arg-type]
            integration=encounter_integration,  # type: ignore[arg-type]
            session=ExplorationEncounterSessionService(encounter_integration),  # type: ignore[arg-type]
            navigation=navigation,
        ),
    )

    response = await gateway.look_around(char_id=7)

    assert response.header.current_state == CoreDomain.EXPLORATION
    assert response.payload_type == "exploration_encounter"
    assert response.payload.content.kind == "encounter"
    assert isinstance(response.payload.content.data, EncounterDTO)
    assert response.payload.content.data.id == "enc-1"


@pytest.mark.asyncio
async def test_look_around_clears_stale_encounter_ref_and_returns_navigation() -> None:
    encounter_integration = FakeEncounterIntegration(active_id="missing", sessions={})
    service = ExplorationService(
        FakeExplorationIntegrator(),
        encounter_engine=FakeEncounterEngine(),
        encounter_integration=encounter_integration,  # type: ignore[arg-type]
    )

    result = await service.look_around(7)

    assert isinstance(result, WorldNavigationDTO)
    assert result.loc_id == "52_51"
    assert encounter_integration.detached == [7]


@pytest.mark.asyncio
async def test_active_encounter_blocks_move_search_and_use_service_progression() -> None:
    encounter = _encounter()
    integrator = FakeExplorationIntegrator()
    encounter_integration = FakeEncounterIntegration(
        active_id="enc-1",
        sessions={"enc-1": {"payload": encounter.model_dump(mode="json")}},
    )
    engine = FakeEncounterEngine()
    service = ExplorationService(
        integrator,
        encounter_engine=engine,
        encounter_integration=encounter_integration,  # type: ignore[arg-type]
    )

    move_result = await service.move(7, target_id="52_52")
    search_result = await service.interact(7, "search")
    service_result = await service.use_service(7, "svc_arena_main")

    assert isinstance(move_result, EncounterDTO)
    assert isinstance(search_result, EncounterDTO)
    assert isinstance(service_result, EncounterDTO)
    assert move_result.id == search_result.id == service_result.id == "enc-1"
    assert integrator.moves == []
    assert engine.calls == []


@pytest.mark.asyncio
async def test_failed_gateway_bypass_routes_active_encounter_to_combat(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.backend.features.exploration.services.encounter_service.random.random",
        lambda: 0.99,
    )
    encounter = _ready_combat_encounter()
    encounter_integration = FakeEncounterIntegration(
        active_id="enc-1",
        sessions={"enc-1": {"payload": encounter.model_dump(mode="json")}},
    )
    navigation = ExplorationNavigationService(FakeExplorationIntegrator())  # type: ignore[arg-type]
    gateway = ExplorationGateway(
        navigation=navigation,
        encounters=ExplorationEncounterService(
            engine=FakeEncounterEngine(),  # type: ignore[arg-type]
            integration=encounter_integration,  # type: ignore[arg-type]
            session=ExplorationEncounterSessionService(encounter_integration),  # type: ignore[arg-type]
            navigation=navigation,
        ),
    )

    response = await gateway.interact(char_id=7, action="bypass")

    assert response.header.current_state == CoreDomain.COMBAT
    assert response.payload_type == "state_transition"
    assert response.payload.combat_id == "combat-enc-1"
    assert response.payload.reason == "exploration_attack"
    assert encounter_integration.progress == [(7, {"skill_scouting": 0.0008, "skill_hunting": 0.0008})]
    assert encounter_integration.combat_sessions == [(7, "combat-enc-1")]
    assert encounter_integration.cleared == ["enc-1"]
    assert encounter_integration.detached == [7]


@pytest.mark.asyncio
async def test_generated_encounter_is_persisted_and_attached_for_restore() -> None:
    encounter = _encounter("enc-new")
    integrator = FakeExplorationIntegrator()
    encounter_integration = FakeEncounterIntegration()
    service = ExplorationService(
        integrator,
        encounter_engine=FakeEncounterEngine(encounter),
        encounter_integration=encounter_integration,  # type: ignore[arg-type]
    )

    result = await service.move(7, target_id="52_52")

    assert isinstance(result, EncounterDTO)
    assert result.id == "enc-new"
    assert integrator.moves == [(7, "52_51", "52_52")]
    assert encounter_integration.attached == [(7, "enc-new")]
    assert encounter_integration.created[0][0] == "enc-new"
    created_payload = encounter_integration.created[0][1]
    assert created_payload["encounter_id"] == "enc-new"
    assert created_payload["char_id"] == 7
    assert created_payload["status"] == "pending"
    assert created_payload["payload"]["id"] == "enc-new"
    assert created_payload["payload"]["metadata"]["navigation"]["loc_id"] == "52_52"


@pytest.mark.asyncio
async def test_active_encounter_without_snapshot_is_hydrated_for_frontend_view() -> None:
    encounter = _encounter()
    encounter_integration = FakeEncounterIntegration(
        active_id="enc-1",
        sessions={"enc-1": {"payload": encounter.model_dump(mode="json")}},
    )
    service = ExplorationService(
        FakeExplorationIntegrator(),
        encounter_engine=FakeEncounterEngine(),
        encounter_integration=encounter_integration,  # type: ignore[arg-type]
    )

    result = await service.look_around(7)

    assert isinstance(result, EncounterDTO)
    assert result.metadata["navigation"]["loc_id"] == "52_51"
    assert encounter_integration.patched[0][0] == "enc-1"
    assert encounter_integration.patched[0][1]["payload"]["metadata"]["navigation"]["loc_id"] == "52_51"
