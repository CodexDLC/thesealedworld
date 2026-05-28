from __future__ import annotations

import pytest

from src.backend.features.rift.dto import RiftStartRequestDTO, RiftZoneCellDTO, RiftZoneRuntimeDTO
from src.backend.features.rift.services.entry_service import RiftEntryService
from src.shared.enums import CoreDomain


class FakeRuntimeIntegration:
    def __init__(self) -> None:
        self.saved_instances: list[RiftZoneRuntimeDTO] = []
        self.sessions: list[dict] = []
        self.presence: list[tuple[str, str, str]] = []

    async def save_instance(self, runtime: RiftZoneRuntimeDTO) -> None:
        self.saved_instances.append(runtime)

    async def create_run_session(self, payload: dict) -> dict:
        self.sessions.append(dict(payload))
        return dict(payload)

    async def enter_node_presence(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        self.presence.append((rift_instance_id, node_id, participant_ref))


class FakeCharacterSessions:
    def __init__(self) -> None:
        self.attached: list[tuple[int, str, dict]] = []
        self.prepared: list[tuple[int, str, dict]] = []
        self.sessions: dict[int, dict] = {
            7: {
                "metrics": {
                    "gear_score": 612,
                }
            }
        }

    async def get_session(self, char_id: int) -> dict | None:
        return self.sessions.get(char_id)

    async def set_rift_session(self, char_id: int, rift_session_id: str, **kwargs) -> None:
        self.attached.append((char_id, rift_session_id, kwargs))

    async def attach_prepared_rift_session(self, char_id: int, rift_session_id: str, **kwargs) -> None:
        self.prepared.append((char_id, rift_session_id, kwargs))


def _runtime() -> RiftZoneRuntimeDTO:
    return RiftZoneRuntimeDTO(
        rift_instance_id="rift-instance-1",
        zone_instance_id="zone-1",
        zone_canvas_key="starter",
        scale_preset_key="starter_5x5",
        assembly_preset_key="starter",
        setting={"setting_key": "starter_rift", "title": "Рваный тракт", "tier": 1},
        population_context={
            "setting_key": "starter_rift",
            "family_bindings": {
                "primary": {
                    "slot_id": "primary",
                    "family_id": "bandit_gang",
                    "clan_id": None,
                    "context_hash": "ctx-primary",
                    "unique_hash": "unique-primary",
                    "source": "rift_static",
                }
            },
        },
        nodes={
            "node-start": RiftZoneCellDTO(
                node_id="node-start",
                x=2,
                y=2,
                pool_node_id="pool-start",
                node_hex="A",
                title="Сухая дорога",
                description="Стартовая точка.",
            )
        },
        cells_by_coord={"2:2": "node-start"},
        start_node_id="node-start",
        finish_node_id="node-start",
        current_node_id="node-start",
        visited_node_ids={"node-start"},
        debug=False,
    )


@pytest.mark.asyncio
async def test_enter_from_scenario_creates_rift_run_and_moves_active_character(monkeypatch) -> None:
    runtime = FakeRuntimeIntegration()
    character_sessions = FakeCharacterSessions()
    service = RiftEntryService(runtime=runtime, character_sessions=character_sessions)

    monkeypatch.setattr(service, "_build_runtime", lambda request: _runtime())

    result = await service.enter_from_scenario(
        char_id=7,
        source_ref="awakening_rift:knockout",
        request=RiftStartRequestDTO(seed="story-seed", debug=False),
    )

    assert result["status"] == "ok"
    assert result["target_state"] == CoreDomain.RIFT.value
    assert result["rift_instance_id"] == "rift-instance-1"
    assert result["rift_session_id"].startswith("rift:run:")
    assert runtime.saved_instances[0].rift_instance_id == "rift-instance-1"
    assert runtime.sessions[0]["owner_id"] == "char:7"
    assert runtime.sessions[0]["participant_ref"] == "char:7"
    assert runtime.sessions[0]["entry_context"] == {
        "source_state": CoreDomain.SCENARIO.value,
        "source_ref": "awakening_rift:knockout",
        "combat_power": {
            "scope": "solo",
            "player_gear_score": 612,
            "party_gear_score": 612,
            "source": "active_character.metrics.gear_score",
        },
    }
    assert runtime.presence == [("rift-instance-1", "node-start", "char:7")]
    assert character_sessions.attached == [
        (
            7,
            result["rift_session_id"],
            {
                "rift_instance_id": "rift-instance-1",
                "prev_state": CoreDomain.SCENARIO,
            },
        )
    ]


@pytest.mark.asyncio
async def test_prepare_from_scenario_creates_rift_run_with_exit_policy_without_switching_state(monkeypatch) -> None:
    runtime = FakeRuntimeIntegration()
    character_sessions = FakeCharacterSessions()
    service = RiftEntryService(runtime=runtime, character_sessions=character_sessions)

    monkeypatch.setattr(service, "_build_runtime", lambda request, *, rift_key=None: _runtime())

    result = await service.prepare_from_scenario(
        char_id=7,
        source_ref="scenario:awakening_rift:crash_sequence_02",
        request_id="rift-request-1",
        exit_policy={
            "target_state": CoreDomain.EXPLORATION.value,
            "location_id": "45_52",
            "reason": "starter_rift_escape",
        },
        request=RiftStartRequestDTO(seed="story-seed", debug=False),
    )

    assert result["status"] == "ok"
    assert result["target_state"] == CoreDomain.SCENARIO.value
    assert runtime.sessions[0]["exit_policy"] == {
        "mode": "heart_exit_only",
        "completion_exit": "from_heart",
        "entrance_seals_on_entry": True,
        "entrance_node_id": "node-start",
        "exit_node_id": "node-start",
        "target_state": CoreDomain.EXPLORATION.value,
        "location_id": "45_52",
        "reason": "starter_rift_escape",
        "close_rift_on_exit": True,
    }
    assert runtime.sessions[0]["entry_context"]["combat_power"] == {
        "scope": "solo",
        "player_gear_score": 612,
        "party_gear_score": 612,
        "source": "active_character.metrics.gear_score",
    }
    assert character_sessions.prepared == [
        (
            7,
            result["rift_session_id"],
            {
                "rift_instance_id": "rift-instance-1",
                "request_id": "rift-request-1",
            },
        )
    ]
    assert character_sessions.attached == []


@pytest.mark.asyncio
async def test_prepare_from_scenario_can_require_return_to_exit_after_heart(monkeypatch) -> None:
    runtime = FakeRuntimeIntegration()
    character_sessions = FakeCharacterSessions()
    service = RiftEntryService(runtime=runtime, character_sessions=character_sessions)

    monkeypatch.setattr(service, "_build_runtime", lambda request, *, rift_key=None: _runtime())

    await service.prepare_from_scenario(
        char_id=7,
        source_ref="scenario:awakening_rift:crash_sequence_02",
        request_id="rift-request-1",
        exit_policy={
            "target_state": CoreDomain.EXPLORATION.value,
            "location_id": "45_52",
            "reason": "starter_rift_escape",
            "completion_exit": "return_to_exit",
            "exit_node_id": "node-start",
        },
        request=RiftStartRequestDTO(seed="story-seed", debug=False),
    )

    assert runtime.sessions[0]["exit_policy"]["completion_exit"] == "return_to_exit"
    assert runtime.sessions[0]["exit_policy"]["exit_node_id"] == "node-start"


@pytest.mark.asyncio
async def test_build_runtime_applies_bootstrapped_family_bindings(monkeypatch) -> None:
    runtime = FakeRuntimeIntegration()
    character_sessions = FakeCharacterSessions()
    service = RiftEntryService(
        runtime=runtime,
        character_sessions=character_sessions,
        rift_population_bindings={
            "starter_rift": {
                "primary": {
                    "slot_id": "primary",
                    "family_id": "bandit_gang",
                    "clan_id": "clan-1",
                    "context_hash": "ctx-primary",
                    "unique_hash": "unique-primary",
                    "source": "rift_static_bootstrap",
                }
            }
        },
    )

    monkeypatch.setattr(
        "src.backend.features.rift.services.entry_service.RiftDevService.build_runtime",
        lambda self, request: _runtime(),
    )

    result = service._build_runtime(RiftStartRequestDTO(seed="story-seed", debug=False))

    assert result.population_context["family_bindings"]["primary"] == {
        "slot_id": "primary",
        "family_id": "bandit_gang",
        "clan_id": "clan-1",
        "context_hash": "ctx-primary",
        "unique_hash": "unique-primary",
        "source": "rift_static_bootstrap",
    }
