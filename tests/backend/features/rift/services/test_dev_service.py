from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.backend.features.rift.dto import (
    RiftActionRequestDTO,
    RiftStartRequestDTO,
    RiftTravelStartRequestDTO,
    RiftTravelTickRequestDTO,
)
from src.backend.features.rift.resources import RiftResourceLoader
from src.backend.features.rift.services import RiftDevService

if TYPE_CHECKING:
    from src.backend.features.rift.dto import RiftZoneRuntimeDTO


class FakeRiftRuntimeIntegration:
    def __init__(self) -> None:
        self.runtime: RiftZoneRuntimeDTO | None = None
        self.sessions: dict[str, dict] = {}
        self.node_presence: dict[tuple[str, str], set[str]] = {}

    async def save_instance(self, runtime: RiftZoneRuntimeDTO) -> None:
        self.runtime = runtime

    async def require_instance(self, rift_instance_id: str) -> RiftZoneRuntimeDTO:
        if self.runtime is None or self.runtime.rift_instance_id != rift_instance_id:
            raise AssertionError(f"Missing test runtime: {rift_instance_id}")
        return self.runtime

    async def create_run_session(self, payload: dict) -> dict:
        self.sessions[payload["rift_session_id"]] = dict(payload)
        return dict(payload)

    async def save_run_session(self, payload: dict) -> None:
        self.sessions[payload["rift_session_id"]] = dict(payload)

    async def get_run_session(self, rift_session_id: str) -> dict | None:
        session = self.sessions.get(rift_session_id)
        return dict(session) if session is not None else None

    async def enter_node_presence(self, rift_instance_id: str, node_id: str, participant_ref: str) -> None:
        self.node_presence.setdefault((rift_instance_id, node_id), set()).add(participant_ref)

    async def move_presence(
        self,
        rift_instance_id: str,
        *,
        from_node_id: str | None,
        to_node_id: str,
        participant_ref: str,
    ) -> None:
        if from_node_id:
            self.node_presence.setdefault((rift_instance_id, from_node_id), set()).discard(participant_ref)
        await self.enter_node_presence(rift_instance_id, to_node_id, participant_ref)


@pytest.mark.unit
async def test_rebuild_resets_runtime_from_random_assembly_presets() -> None:
    manager = FakeRiftRuntimeIntegration()
    service = RiftDevService(runtime=manager, resources=RiftResourceLoader())
    await service.start(RiftStartRequestDTO(seed="dev-start", assembly_preset_key="grid_5x5_active_15"))
    assert manager.runtime is not None
    original_runtime = manager.runtime
    moved_runtime = original_runtime.model_copy(
        update={
            "current_node_id": next(node_id for node_id in original_runtime.nodes if node_id != original_runtime.start_node_id),
            "visited_node_ids": {original_runtime.start_node_id, original_runtime.finish_node_id},
            "last_travel": {"kind": "exploration"},
        }
    )
    manager.runtime = moved_runtime

    await service.rebuild(original_runtime.rift_instance_id, seed="dev-rebuild", void_cells=None)

    assert manager.runtime is not None
    assert manager.runtime.rift_instance_id == original_runtime.rift_instance_id
    assert manager.runtime.current_node_id == manager.runtime.start_node_id
    assert manager.runtime.visited_node_ids == {manager.runtime.start_node_id}
    assert manager.runtime.last_travel is None
    assert manager.runtime.assembly_preset_key == "grid_5x5_active_15"
    session = manager.sessions[f"dev:{original_runtime.rift_instance_id}:run"]
    assert session["current_node_id"] == manager.runtime.start_node_id
    assert session["visited_node_ids"] == [manager.runtime.start_node_id]
    assert session["last_travel"] is None


@pytest.mark.unit
async def test_travel_tick_can_return_transition_combat_prompt() -> None:
    manager = FakeRiftRuntimeIntegration()
    service = RiftDevService(runtime=manager, resources=RiftResourceLoader())
    screen = None
    combat_capable_moves = []
    for index in range(20):
        screen = await service.start(
            RiftStartRequestDTO(seed=f"travel-combat-check-{index}", assembly_preset_key="grid_5x5_active_15")
        )
        combat_capable_moves = [
            action
            for action in screen.movement
            if action.action == "move" and action.target_node_id and action.travel and action.travel.can_trigger_event
        ]
        if combat_capable_moves:
            break
    assert screen is not None
    assert combat_capable_moves, [(action.action, action.target_node_id, action.state, action.travel) for action in screen.movement]
    first_move = combat_capable_moves[0]

    started = await service.start_travel(
        screen.meta.rift_instance_id,
        RiftTravelStartRequestDTO(target_node_id=first_move.target_node_id or ""),
    )

    assert manager.runtime is not None
    assert manager.runtime.active_travel is None
    session = manager.sessions[f"dev:{screen.meta.rift_instance_id}:run"]
    assert session["active_travel"] is not None
    assert started.travel.status == "moving"
    assert started.travel.to_node_id == first_move.target_node_id
    assert started.combat_prompt is None

    ticked = await service.tick_travel(
        screen.meta.rift_instance_id,
        RiftTravelTickRequestDTO(travel_id=started.travel.travel_id, force_event="combat"),
    )

    session = manager.sessions[f"dev:{screen.meta.rift_instance_id}:run"]
    assert manager.runtime.active_travel is None
    assert session["active_travel"] is not None
    assert session["active_travel"]["status"] == "interrupted"
    assert ticked.travel.status == "interrupted"
    assert ticked.travel.tick_result == "combat"
    assert ticked.combat_prompt is not None
    assert ticked.combat_prompt.source == "rift_transition"
    assert ticked.combat_prompt.enemies
    assert ticked.combat_prompt.actions[0].id == "attack"
    assert ticked.combat_prompt.actions[0].label == "В бой!"
    assert ticked.combat_prompt.metadata["travel_id"] == started.travel.travel_id
    assert ticked.combat_prompt.metadata["encounter_descriptor_key"]
    opening_context = ticked.combat_prompt.metadata["opening_context"]
    assert opening_context["status"] == "contract_placeholder"
    assert opening_context["resolved"] is False
    assert opening_context["applies_to"] == ["rift_transition_combat", "future_world_travel_combat"]
    assert {
        item["skill_key"]
        for item in opening_context["skill_hooks"]
    } == {
        "skill_scouting",
        "skill_pathfinder",
        "skill_hunting",
        "skill_adaptation",
        "skill_tactics",
    }
    assert "разлом выбрасывает угрозу" not in ticked.combat_prompt.description
    descriptors = RiftResourceLoader().load_setting("starter_rift")["encounter_vocabulary"]["transition_combat"]
    assert ticked.combat_prompt.title in {item["title"] for item in descriptors}

    resolved = await service.run_action(
        screen.meta.rift_instance_id,
        RiftActionRequestDTO(
            action_type="resolve_transition_combat",
            payload={"travel_id": started.travel.travel_id, "result": "victory"},
        ),
    )

    session = manager.sessions[f"dev:{screen.meta.rift_instance_id}:run"]
    assert manager.runtime.active_travel is None
    assert manager.runtime.current_node_id == manager.runtime.start_node_id
    assert manager.runtime.last_travel is None
    assert session["active_travel"] is None
    assert session["current_node_id"] == first_move.target_node_id
    assert session["last_travel"] is not None
    assert session["last_travel"]["event_triggered"] is True
    assert session["last_travel"]["event_type"] == "combat"
    assert session["last_travel"]["resolved"] is True
    assert session["last_travel"]["result"] == "victory"
    assert session["last_travel"]["suppress_random_node_combat"] is True
    assert resolved.action_type == "resolve_transition_combat"
    assert resolved.result == "victory"
    assert resolved.screen.current_node.node_id == first_move.target_node_id
