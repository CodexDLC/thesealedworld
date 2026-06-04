from __future__ import annotations

import pytest

from src.backend.features.rift.dto import (
    RiftActionRequestDTO,
    RiftCombatPromptDTO,
    RiftPassageEdgeDTO,
    RiftTravelStartRequestDTO,
    RiftTravelTickRequestDTO,
    RiftZoneCellDTO,
    RiftZoneRuntimeDTO,
)
from src.backend.features.rift.integrations import RiftRuntimeIntegration, RiftRuntimeNotFoundError
from src.backend.features.rift.services.player_service import RiftPlayerService
from src.backend.infrastructure.rift.managers import RiftInstanceNotFoundError, RiftRunSessionNotFoundError


class FakeRuntimeIntegration:
    def __init__(self, *, session: dict | None = None, instance: RiftZoneRuntimeDTO | None = None) -> None:
        self.session = session
        self.instance = instance
        self.saved_sessions: list[dict] = []
        self.saved_instances: list[RiftZoneRuntimeDTO] = []
        self.moved_presence: list[tuple[str, str | None, str, str]] = []
        self.left_presence: list[tuple[str, str, str]] = []

    async def require_instance(self, rift_instance_id: str) -> RiftZoneRuntimeDTO:
        assert rift_instance_id == "rift-instance-1"
        return self.instance or RiftZoneRuntimeDTO(
            rift_instance_id="rift-instance-1",
            zone_instance_id="zone-1",
            zone_canvas_key="starter",
            scale_preset_key="starter_5x5",
            assembly_preset_key="starter",
            setting={"title": "Рваный тракт", "tier": 1},
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
            current_node_id="node-old",
            visited_node_ids={"node-old"},
        )

    async def require_run_session(self, rift_session_id: str) -> dict:
        assert rift_session_id == "rift-run-1"
        return self.session or {
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
            "zone_instance_id": "zone-1",
            "current_zone_key": "z01",
            "current_node_id": "node-start",
            "previous_node_id": None,
            "heading": None,
            "visited_node_ids": ["node-start"],
            "active_travel": None,
            "last_travel": None,
            "participant_ref": "char:7",
            "exit_policy": {
                "mode": "heart_exit_only",
                "entrance_seals_on_entry": True,
                "target_state": "exploration",
                "location_id": "45_52",
                "close_rift_on_exit": True,
            },
        }

    async def save_run_session(self, payload: dict) -> None:
        self.session = dict(payload)
        self.saved_sessions.append(dict(payload))

    async def save_instance(self, runtime: RiftZoneRuntimeDTO) -> None:
        self.instance = runtime
        self.saved_instances.append(runtime)

    async def move_presence(
        self,
        rift_instance_id: str,
        *,
        from_node_id: str | None,
        to_node_id: str,
        participant_ref: str,
    ) -> None:
        self.moved_presence.append((rift_instance_id, from_node_id, to_node_id, participant_ref))

    async def leave_node_presence(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        self.left_presence.append((rift_instance_id, node_id, participant_ref))


class FakeGameConfig:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    async def get_float(self, namespace: str, key: str, default: float) -> float:
        assert namespace == "rift"
        return float(self.values.get(key, default))

    async def get_int(self, namespace: str, key: str, default: int) -> int:
        assert namespace == "rift"
        return int(self.values.get(key, default))

    async def get_bool(self, namespace: str, key: str, default: bool) -> bool:
        assert namespace == "rift"
        return bool(self.values.get(key, default))


FAST_RIFT_CONFIG = FakeGameConfig(
    {
        "TRANSITION_EXPLORATION_DURATION_MS": 2000,
        "TRANSITION_TICK_INTERVAL_MS": 2000,
    }
)
FAST_RIFT_ORDINARY_COMBAT_CONFIG = FakeGameConfig(
    {
        "TRANSITION_EXPLORATION_DURATION_MS": 2000,
        "TRANSITION_TICK_INTERVAL_MS": 2000,
        "ORDINARY_NODE_COMBAT_CHANCE": 1.0,
    }
)


class FakeCharacterSessions:
    def __init__(self, *, document: dict | None = None) -> None:
        self.document = document
        self.cleared: list[int] = []
        self.states: list[tuple[int, str, str | None]] = []
        self.locations: list[tuple[int, str, str | None]] = []
        self.symbiote_xp: list[tuple[int, int]] = []

    async def get_session(self, char_id: int) -> dict:
        assert char_id == 7
        return self.document or {
            "state": "rift",
            "sessions": {
                "rift_session_id": "rift-run-1",
                "rift_instance_id": "rift-instance-1",
            },
        }

    async def clear_rift_session(self, char_id: int) -> None:
        self.cleared.append(char_id)

    async def set_state(self, char_id: int, state: str, *, prev_state: str | None = None) -> None:
        self.states.append((char_id, state, prev_state))

    async def set_location(self, char_id: int, location_id: str, *, prev: str | None = None) -> None:
        self.locations.append((char_id, location_id, prev))

    async def apply_symbiote_xp(self, char_id: int, amount: int) -> dict:
        self.symbiote_xp.append((char_id, amount))
        return {"gift_xp": amount}


class FakeRiftCombatLauncher:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def launch_combat_from_prompt(
        self,
        runtime: RiftZoneRuntimeDTO,
        *,
        session: dict,
        prompt: RiftCombatPromptDTO,
    ) -> RiftCombatPromptDTO:
        metadata = dict(prompt.metadata)
        self.calls.append(
            {
                "rift_instance_id": runtime.rift_instance_id,
                "rift_session_id": session["rift_session_id"],
                "event_scope": metadata.get("event_scope"),
                "travel_id": metadata.get("travel_id"),
                "event_key": metadata.get("event_key"),
                "to_node_id": metadata.get("to_node_id"),
            }
        )
        metadata["combat"] = {"status": "started", "combat_id": "combat-rift-1"}
        return prompt.model_copy(update={"metadata": metadata})


class ColdMissingInstanceStore:
    def __init__(self) -> None:
        self.saved: list[RiftZoneRuntimeDTO] = []

    async def save_instance(self, runtime: RiftZoneRuntimeDTO) -> None:
        self.saved.append(runtime)

    async def get_instance(self, rift_instance_id: str) -> RiftZoneRuntimeDTO | None:
        _ = rift_instance_id
        return self.saved[-1] if self.saved else None

    async def require_instance(self, rift_instance_id: str) -> RiftZoneRuntimeDTO:
        if self.saved:
            return self.saved[-1]
        raise RiftInstanceNotFoundError(f"Rift instance not found: {rift_instance_id}")


class ColdMissingRunSessionStore:
    def __init__(self) -> None:
        self.created: list[dict] = []

    async def create_session(self, payload: dict) -> dict:
        self.created.append(dict(payload))
        return payload

    async def require_session(self, rift_session_id: str) -> dict:
        for session in self.created:
            if session.get("rift_session_id") == rift_session_id:
                return session
        raise RiftRunSessionNotFoundError(f"Rift run session not found: {rift_session_id}")


class ColdPresenceStore:
    def __init__(self) -> None:
        self.entered: list[tuple[str, str, str]] = []

    async def rebuild_node_presence_from_sessions(self, rift_instance_id: str, sessions: dict[str, dict]) -> None:
        for session in sessions.values():
            self.entered.append((rift_instance_id, session["current_node_id"], session["participant_ref"]))


class ColdMembership:
    rift_instance_id = "rift-instance-1"
    rift_session_id = "rift-run-1"
    participant_ref = "char:7"
    status = "active"


class ColdMembershipRepository:
    def __init__(self, membership: object | None) -> None:
        self.membership = membership

    async def get_by_session(self, rift_session_id: str) -> object | None:
        _ = rift_session_id
        return self.membership


class ColdSnapshotRepository:
    def __init__(self, snapshot: dict | None) -> None:
        self.snapshot = snapshot

    async def get_snapshot(self, rift_instance_id: str) -> dict | None:
        _ = rift_instance_id
        return self.snapshot


@pytest.mark.asyncio
async def test_player_service_builds_screen_from_active_character_rift_refs() -> None:
    service = RiftPlayerService(
        runtime=FakeRuntimeIntegration(),
        character_sessions=FakeCharacterSessions(),
    )

    screen = await service.screen(7)

    assert screen.meta.rift_instance_id == "rift-instance-1"
    assert screen.current_node.node_id == "node-start"
    assert screen.exit.mode == "heart_exit_only"
    assert screen.exit.entrance_seals_on_entry is True
    assert screen.exit.can_leave is False


@pytest.mark.asyncio
async def test_player_service_cold_restores_screen_from_db_backups_when_redis_runtime_expired() -> None:
    instance_store = ColdMissingInstanceStore()
    session_store = ColdMissingRunSessionStore()
    instance = _two_node_runtime()
    run_session = {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "zone_instance_id": "zone-1",
        "current_zone_key": "z01",
        "current_node_id": "node-next",
        "previous_node_id": "node-start",
        "heading": "north",
        "visited_node_ids": ["node-start", "node-next"],
        "active_travel": None,
        "last_travel": None,
        "participant_ref": "char:7",
    }
    runtime = RiftRuntimeIntegration(
        instance_store=instance_store,  # type: ignore[arg-type]
        session_store=session_store,  # type: ignore[arg-type]
        presence_store=ColdPresenceStore(),  # type: ignore[arg-type]
        membership_repository=ColdMembershipRepository(ColdMembership()),  # type: ignore[arg-type]
        snapshot_repository=ColdSnapshotRepository(
            {
                "rift_instance_id": "rift-instance-1",
                "instance": instance.model_dump(mode="json"),
                "sessions": {"rift-run-1": run_session},
                "presence": {},
            }
        ),  # type: ignore[arg-type]
    )
    service = RiftPlayerService(runtime=runtime, character_sessions=FakeCharacterSessions())

    screen = await service.screen(7)

    assert screen.meta.rift_instance_id == "rift-instance-1"
    assert screen.current_node.node_id == "node-next"
    assert instance_store.saved == [instance]
    assert session_store.created == [run_session]


@pytest.mark.asyncio
async def test_player_service_keeps_missing_rift_not_found_when_redis_and_db_backup_are_absent() -> None:
    instance_store = ColdMissingInstanceStore()
    session_store = ColdMissingRunSessionStore()
    runtime = RiftRuntimeIntegration(
        instance_store=instance_store,  # type: ignore[arg-type]
        session_store=session_store,  # type: ignore[arg-type]
        presence_store=ColdPresenceStore(),  # type: ignore[arg-type]
        membership_repository=ColdMembershipRepository(ColdMembership()),  # type: ignore[arg-type]
        snapshot_repository=ColdSnapshotRepository(None),  # type: ignore[arg-type]
    )
    service = RiftPlayerService(runtime=runtime, character_sessions=FakeCharacterSessions())

    with pytest.raises(RiftRuntimeNotFoundError, match="Rift instance not found: rift-instance-1"):
        await service.screen(7)

    assert instance_store.saved == []
    assert session_store.created == []


@pytest.mark.asyncio
async def test_player_service_uses_active_character_attributes_for_blocker_actions() -> None:
    instance = _two_node_runtime().model_copy(
        update={
            "passage_edges": {
                "node-start:north": RiftPassageEdgeDTO(
                    from_node_id="node-start",
                    to_node_id="node-next",
                    absolute_direction="north",
                    state="blocked_temporary",
                    blocker_key="jammed_service_gate",
                    requirement={
                        "mode": "single_attribute",
                        "check": {
                            "kind": "attribute",
                            "key": "dexterity",
                            "dc": 15,
                            "label": "Пролезть в просвет",
                        },
                    },
                )
            }
        }
    )
    runtime = FakeRuntimeIntegration(instance=instance)
    character_sessions = FakeCharacterSessions(
        document={
            "state": "rift",
            "attributes": {"dexterity": 16},
            "sessions": {
                "rift_session_id": "rift-run-1",
                "rift_instance_id": "rift-instance-1",
            },
        }
    )
    service = RiftPlayerService(runtime=runtime, character_sessions=character_sessions)

    screen = await service.screen(7)
    action = next(item for item in screen.movement if item.target_node_id == "node-next")

    assert action.label == "Пролезть в просвет"
    assert action.style == "primary"
    assert action.is_active is True
    assert action.tooltip == "Требуется: Ловкость 15. У тебя: 16. Можно пройти."
    assert action.debug_text_parts["check_result"]["current_value"] == 16

    response = await service.run_action(
        7,
        RiftActionRequestDTO(
            action_type="resolve_blocker",
            target_node_id="node-next",
            direction="north",
        ),
    )

    assert response.result == "success"
    assert response.details["attribute_value"] == 16
    assert runtime.saved_sessions[-1]["current_node_id"] == "node-next"
    assert runtime.saved_sessions[-1]["previous_node_id"] == "node-start"
    assert runtime.moved_presence == [("rift-instance-1", "node-start", "node-next", "char:7")]


@pytest.mark.asyncio
async def test_player_service_treats_dexterity_blocker_as_agility_attribute() -> None:
    instance = _two_node_runtime().model_copy(
        update={
            "passage_edges": {
                "node-start:north": RiftPassageEdgeDTO(
                    from_node_id="node-start",
                    to_node_id="node-next",
                    absolute_direction="north",
                    state="blocked_temporary",
                    blocker_key="jammed_service_gate",
                    requirement={
                        "mode": "single_attribute",
                        "check": {
                            "kind": "attribute",
                            "key": "dexterity",
                            "dc": 15,
                            "label": "Пролезть в просвет",
                        },
                    },
                )
            }
        }
    )
    runtime = FakeRuntimeIntegration(instance=instance)
    character_sessions = FakeCharacterSessions(
        document={
            "state": "rift",
            "attributes": {"agility": 17},
            "sessions": {
                "rift_session_id": "rift-run-1",
                "rift_instance_id": "rift-instance-1",
            },
        }
    )
    service = RiftPlayerService(runtime=runtime, character_sessions=character_sessions)

    screen = await service.screen(7)
    action = next(item for item in screen.movement if item.target_node_id == "node-next")

    assert action.is_active is True
    assert action.tooltip == "Требуется: Ловкость 15. У тебя: 17. Можно пройти."

    response = await service.run_action(
        7,
        RiftActionRequestDTO(
            action_type="resolve_blocker",
            target_node_id="node-next",
            direction="north",
        ),
    )

    assert response.result == "success"
    assert response.details["attribute_value"] == 17
    assert runtime.saved_sessions[-1]["current_node_id"] == "node-next"
    assert runtime.saved_sessions[-1]["previous_node_id"] == "node-start"


@pytest.mark.asyncio
async def test_player_service_starts_real_combat_when_travel_tick_triggers_encounter() -> None:
    instance = _two_node_runtime()
    runtime = FakeRuntimeIntegration(instance=instance)
    encounters = FakeRiftCombatLauncher()
    service = RiftPlayerService(
        runtime=runtime,
        character_sessions=FakeCharacterSessions(),
        encounters=encounters,
        game_config=FAST_RIFT_CONFIG,
    )

    started = await service.start_travel(7, RiftTravelStartRequestDTO(target_node_id="node-next"))
    ticked = await service.tick_travel(
        7,
        RiftTravelTickRequestDTO(travel_id=started.travel.travel_id, force_event="combat"),
    )

    assert ticked.combat_prompt is not None
    assert ticked.combat_prompt.metadata["combat"] == {"status": "started", "combat_id": "combat-rift-1"}
    assert encounters.calls == [
        {
            "rift_instance_id": "rift-instance-1",
            "rift_session_id": "rift-run-1",
            "event_scope": "transition",
            "travel_id": started.travel.travel_id,
            "event_key": None,
            "to_node_id": "node-next",
        }
    ]
    assert runtime.saved_sessions[-1]["active_travel"]["status"] == "interrupted"


@pytest.mark.asyncio
async def test_player_service_starts_required_node_entry_combat_after_arrival_without_transition_combat() -> None:
    instance = _two_node_runtime().model_copy(
        update={
            "node_events": {
                "node-next": {
                    "event_key": "guard_combat",
                    "event_type": "combat",
                    "state": "ready",
                    "is_required": True,
                    "title": "Охрана узла",
                    "description": "Группа держит проход.",
                    "grants_flags": ["rift_flag:guarded_node:heart:cleared"],
                    "unlocks": [{"kind": "passage", "gate_key": "guarded_node:heart", "target_node_id": "heart"}],
                    "combat": {"status": "placeholder", "budget_policy": "guard_node_plus_gear_score"},
                }
            },
            "node_states": {"node-next": {"entry_event_state": "ready", "event_key": "guard_combat"}},
        }
    )
    runtime = FakeRuntimeIntegration(instance=instance)
    encounters = FakeRiftCombatLauncher()
    service = RiftPlayerService(
        runtime=runtime,
        character_sessions=FakeCharacterSessions(),
        encounters=encounters,
        game_config=FAST_RIFT_CONFIG,
    )

    started = await service.start_travel(7, RiftTravelStartRequestDTO(target_node_id="node-next"))
    ticked = await service.tick_travel(
        7,
        RiftTravelTickRequestDTO(travel_id=started.travel.travel_id, force_event="combat"),
    )

    assert ticked.travel.status == "completed"
    assert ticked.combat_prompt is not None
    assert ticked.combat_prompt.metadata["event_scope"] == "node_entry"
    assert ticked.combat_prompt.metadata["event_key"] == "guard_combat"
    assert ticked.combat_prompt.metadata["combat"] == {"status": "started", "combat_id": "combat-rift-1"}
    assert runtime.saved_sessions[-1]["current_node_id"] == "node-next"
    assert runtime.saved_sessions[-1]["active_travel"] is None
    assert runtime.saved_sessions[-1]["last_travel"]["event_triggered"] is False
    assert encounters.calls == [
        {
            "rift_instance_id": "rift-instance-1",
            "rift_session_id": "rift-run-1",
            "event_scope": "node_entry",
            "travel_id": None,
            "event_key": "guard_combat",
            "to_node_id": "node-next",
        }
    ]


@pytest.mark.asyncio
async def test_player_service_starts_ordinary_node_entry_combat_after_arrival() -> None:
    instance = _two_node_runtime()
    runtime = FakeRuntimeIntegration(instance=instance)
    encounters = FakeRiftCombatLauncher()
    service = RiftPlayerService(
        runtime=runtime,
        character_sessions=FakeCharacterSessions(),
        encounters=encounters,
        game_config=FAST_RIFT_ORDINARY_COMBAT_CONFIG,
    )

    started = await service.start_travel(7, RiftTravelStartRequestDTO(target_node_id="node-next"))
    ticked = await service.tick_travel(
        7,
        RiftTravelTickRequestDTO(travel_id=started.travel.travel_id, force_event="none"),
    )

    assert ticked.travel.status == "completed"
    assert ticked.combat_prompt is not None
    assert ticked.combat_prompt.metadata["event_scope"] == "node_entry"
    assert ticked.combat_prompt.metadata["event_key"] == "ordinary_combat"
    assert ticked.combat_prompt.metadata["encounter_kind"] == "ordinary_node"
    assert ticked.combat_prompt.metadata["combat"] == {"status": "started", "combat_id": "combat-rift-1"}
    assert runtime.saved_sessions[-1]["current_node_id"] == "node-next"
    assert runtime.saved_sessions[-1]["active_travel"] is None
    assert encounters.calls == [
        {
            "rift_instance_id": "rift-instance-1",
            "rift_session_id": "rift-run-1",
            "event_scope": "node_entry",
            "travel_id": None,
            "event_key": "ordinary_combat",
            "to_node_id": "node-next",
        }
    ]


@pytest.mark.asyncio
async def test_player_service_rejects_manual_required_node_combat_resolution() -> None:
    instance = _two_node_runtime().model_copy(
        update={
            "current_node_id": "node-next",
            "visited_node_ids": {"node-start", "node-next"},
            "node_events": {
                "node-next": {
                    "event_key": "guard_combat",
                    "event_type": "combat",
                    "state": "ready",
                    "is_required": True,
                }
            },
        }
    )
    session = {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "zone_instance_id": "zone-1",
        "current_zone_key": "z01",
        "current_node_id": "node-next",
        "previous_node_id": "node-start",
        "heading": "north",
        "visited_node_ids": ["node-start", "node-next"],
        "active_travel": None,
        "last_travel": None,
        "participant_ref": "char:7",
    }
    service = RiftPlayerService(
        runtime=FakeRuntimeIntegration(session=session, instance=instance),
        character_sessions=FakeCharacterSessions(),
    )

    with pytest.raises(ValueError, match="Node combat must be resolved by combat result"):
        await service.run_action(
            7,
            RiftActionRequestDTO(action_type="resolve_node_event", event_key="guard_combat", result="victory"),
        )


@pytest.mark.asyncio
async def test_player_service_rejects_manual_ordinary_node_combat_resolution() -> None:
    instance = _two_node_runtime().model_copy(
        update={
            "current_node_id": "node-next",
            "visited_node_ids": {"node-start", "node-next"},
            "node_events": {
                "node-next": {
                    "event_key": "ordinary_combat",
                    "event_type": "combat",
                    "state": "ready",
                    "source": "ordinary_roll",
                    "is_required": False,
                }
            },
        }
    )
    session = {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "zone_instance_id": "zone-1",
        "current_zone_key": "z01",
        "current_node_id": "node-next",
        "previous_node_id": "node-start",
        "heading": "north",
        "visited_node_ids": ["node-start", "node-next"],
        "active_travel": None,
        "last_travel": None,
        "participant_ref": "char:7",
    }
    service = RiftPlayerService(
        runtime=FakeRuntimeIntegration(session=session, instance=instance),
        character_sessions=FakeCharacterSessions(),
    )

    with pytest.raises(ValueError, match="Node combat must be resolved by combat result"):
        await service.run_action(
            7,
            RiftActionRequestDTO(action_type="resolve_node_event", event_key="ordinary_combat", result="victory"),
        )


@pytest.mark.asyncio
async def test_player_service_completes_rift_after_heart_and_uses_exit_policy() -> None:
    instance = await FakeRuntimeIntegration().require_instance("rift-instance-1")
    instance = instance.model_copy(
        update={
            "heart_state": {
                "node_id": "node-start",
                "status": "shattered",
                "can_exit": True,
                "completion": {"status": "completed"},
                "reward": {"symbiote_xp": 25, "resource_value": 25, "resource_template_id": "currency_dust"},
            }
        }
    )
    runtime = FakeRuntimeIntegration(instance=instance)
    character_sessions = FakeCharacterSessions()
    service = RiftPlayerService(runtime=runtime, character_sessions=character_sessions)

    result = await service.complete(7)

    assert result.target_state == "exploration"
    assert result.location_id == "45_52"
    assert result.exit_reason == "completed"
    assert character_sessions.locations == [(7, "45_52", None)]
    assert character_sessions.states == [(7, "exploration", "rift")]
    assert character_sessions.symbiote_xp == [(7, 25)]
    assert character_sessions.cleared == [7]
    assert runtime.left_presence == [("rift-instance-1", "node-start", "char:7")]
    assert runtime.saved_sessions[0]["status"] == "completed"
    assert runtime.saved_sessions[0]["exit_result"]["symbiote_reward"] == {"gift_xp": 25}


@pytest.mark.asyncio
async def test_player_service_rejects_return_to_exit_completion_away_from_exit_node() -> None:
    session = {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "zone_instance_id": "zone-1",
        "current_zone_key": "z01",
        "current_node_id": "node-heart",
        "previous_node_id": "node-start",
        "heading": None,
        "visited_node_ids": ["node-start", "node-heart"],
        "active_travel": None,
        "last_travel": None,
        "participant_ref": "char:7",
        "exit_policy": {
            "mode": "heart_exit_only",
            "completion_exit": "return_to_exit",
            "exit_node_id": "node-start",
            "target_state": "exploration",
            "location_id": "45_52",
            "close_rift_on_exit": True,
        },
    }
    instance = await FakeRuntimeIntegration(session=session).require_instance("rift-instance-1")
    instance = instance.model_copy(
        update={
            "heart_state": {
                "node_id": "node-heart",
                "status": "shattered",
                "can_exit": True,
                "completion": {"status": "completed"},
                "reward": {"symbiote_xp": 25},
            }
        }
    )
    runtime = FakeRuntimeIntegration(instance=instance, session=session)
    service = RiftPlayerService(runtime=runtime, character_sessions=FakeCharacterSessions())

    with pytest.raises(ValueError, match="return to the rift exit"):
        await service.complete(7)


@pytest.mark.asyncio
async def test_player_service_completes_return_to_exit_rift_on_exit_node() -> None:
    session = {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "zone_instance_id": "zone-1",
        "current_zone_key": "z01",
        "current_node_id": "node-start",
        "previous_node_id": "node-heart",
        "heading": None,
        "visited_node_ids": ["node-start", "node-heart"],
        "active_travel": None,
        "last_travel": None,
        "participant_ref": "char:7",
        "exit_policy": {
            "mode": "heart_exit_only",
            "completion_exit": "return_to_exit",
            "exit_node_id": "node-start",
            "target_state": "exploration",
            "location_id": "45_52",
            "close_rift_on_exit": True,
        },
    }
    instance = await FakeRuntimeIntegration(session=session).require_instance("rift-instance-1")
    instance = instance.model_copy(
        update={
            "heart_state": {
                "node_id": "node-heart",
                "status": "shattered",
                "can_exit": True,
                "completion": {"status": "completed"},
                "reward": {"symbiote_xp": 25},
            }
        }
    )
    runtime = FakeRuntimeIntegration(instance=instance, session=session)
    character_sessions = FakeCharacterSessions()
    service = RiftPlayerService(runtime=runtime, character_sessions=character_sessions)

    result = await service.complete(7)

    assert result.exit_reason == "completed"
    assert character_sessions.symbiote_xp == [(7, 25)]
    assert runtime.saved_sessions[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_player_service_rejects_completion_before_heart_exit_is_available() -> None:
    runtime = FakeRuntimeIntegration()
    service = RiftPlayerService(runtime=runtime, character_sessions=FakeCharacterSessions())

    with pytest.raises(ValueError, match="completion is not available"):
        await service.complete(7)


@pytest.mark.asyncio
async def test_player_service_leaves_entrance_return_only_rift_from_start_node() -> None:
    session = {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "zone_instance_id": "zone-1",
        "current_zone_key": "z01",
        "current_node_id": "node-start",
        "previous_node_id": None,
        "heading": None,
        "visited_node_ids": ["node-start"],
        "active_travel": None,
        "last_travel": None,
        "participant_ref": "char:7",
        "exit_policy": {
            "mode": "entrance_return_only",
            "entrance_seals_on_entry": False,
            "entrance_node_id": "node-start",
            "target_state": "exploration",
            "location_id": "52_52",
            "close_rift_on_exit": False,
        },
    }
    runtime = FakeRuntimeIntegration(session=session)
    character_sessions = FakeCharacterSessions()
    service = RiftPlayerService(runtime=runtime, character_sessions=character_sessions)

    result = await service.leave(7)

    assert result.exit_reason == "left"
    assert result.close_rift_on_exit is False
    assert character_sessions.locations == [(7, "52_52", None)]
    assert character_sessions.states == [(7, "exploration", "rift")]
    assert character_sessions.cleared == [7]
    assert runtime.saved_sessions[0]["status"] == "left"


@pytest.mark.asyncio
async def test_player_service_rejects_leave_when_not_at_entrance() -> None:
    session = {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "zone_instance_id": "zone-1",
        "current_zone_key": "z01",
        "current_node_id": "node-deep",
        "visited_node_ids": ["node-start", "node-deep"],
        "participant_ref": "char:7",
        "exit_policy": {
            "mode": "entrance_return_only",
            "entrance_seals_on_entry": False,
            "entrance_node_id": "node-start",
            "target_state": "exploration",
            "location_id": "52_52",
        },
    }
    runtime = FakeRuntimeIntegration(session=session)
    service = RiftPlayerService(runtime=runtime, character_sessions=FakeCharacterSessions())

    with pytest.raises(ValueError, match="entrance node"):
        await service.leave(7)


def _two_node_runtime() -> RiftZoneRuntimeDTO:
    return RiftZoneRuntimeDTO(
        rift_instance_id="rift-instance-1",
        zone_instance_id="zone-1",
        zone_canvas_key="starter",
        scale_preset_key="starter_5x5",
        assembly_preset_key="starter",
        setting={"title": "Рваный тракт", "tier": 1},
        nodes={
            "node-start": RiftZoneCellDTO(
                node_id="node-start",
                x=2,
                y=2,
                pool_node_id="pool-start",
                node_hex="A",
                title="Сухая дорога",
                description="Стартовая точка.",
            ),
            "node-next": RiftZoneCellDTO(
                node_id="node-next",
                x=2,
                y=1,
                pool_node_id="pool-next",
                node_hex="B",
                title="Разбитая повозка",
                description="Пыль и щепки.",
            ),
        },
        cells_by_coord={"2:2": "node-start", "2:1": "node-next"},
        passage_edges={
            "node-start:north": RiftPassageEdgeDTO(
                from_node_id="node-start",
                to_node_id="node-next",
                absolute_direction="north",
                state="open",
            )
        },
        start_node_id="node-start",
        finish_node_id="node-next",
        current_node_id="node-start",
        visited_node_ids={"node-start"},
    )
