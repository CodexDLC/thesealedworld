from __future__ import annotations

import pytest

from src.backend.features.monsters.dto import MonsterGroupMemberPreview, MonsterGroupResult
from src.backend.features.rift.dto import (
    RiftCombatPromptActionDTO,
    RiftCombatPromptDTO,
    RiftZoneCellDTO,
    RiftZoneRuntimeDTO,
)
from src.backend.features.rift.services.encounter_service import RiftEncounterService


class FakeMonsterGroupService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def prepare_monster_group_from_clan(self, clan_id, budget, **kwargs) -> MonsterGroupResult:
        self.calls.append({"clan_id": str(clan_id), "budget": budget, **kwargs})
        return MonsterGroupResult(
            group_id="rift:encounter:1",
            group_key="monster_group:rift:encounter:1",
            clan_id=str(clan_id),
            family_id="bandit_gang",
            loc_id=kwargs["loc_id"],
            zone_id=kwargs["zone_id"],
            biome_id=kwargs["biome_id"],
            tier=kwargs["tier"],
            danger=kwargs["danger"],
            target_budget=budget,
            adjusted_budget=budget,
            total_power=300,
            monster_ids=["monster-1"],
            actor_commitments={"monster:monster-1": "actor:snapshot:monster-1"},
            previews=[
                MonsterGroupMemberPreview(
                    monster_id="monster-1",
                    name="Дорожный налетчик",
                    description="Он выходит из пыли.",
                    role="minion",
                    variant_key="raider",
                    member_tier=1,
                    threat_rating=300,
                    hp={"cur": 100, "max": 100},
                )
            ],
            reused_existing_clan=True,
            context_hash="ctx-primary",
            unique_hash="unique-primary",
            tags=["starter_rift"],
        )


class FakeCombatCreator:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def create_from_request(self, request: dict) -> dict:
        self.requests.append(dict(request))
        return {
            "status": "ready",
            "combat_id": str(request["combat_id"]),
            "battle_type": str(request["battle_type"]),
            "participants": request["participants"],
        }


class FakeRuntimeIntegration:
    def __init__(self) -> None:
        self.active_encounters: list[tuple[str, str]] = []
        self.joined_encounters: list[tuple[str, str, str]] = []
        self.applied_results: list[dict] = []
        self.cleared_encounters: list[str] = []
        self.cleared_encounter_presence: list[tuple[str, str]] = []

    async def set_run_active_encounter(self, rift_session_id: str, encounter_id: str) -> None:
        self.active_encounters.append((rift_session_id, encounter_id))

    async def join_transition_encounter(self, rift_instance_id: str, encounter_id: str, participant_ref: str) -> None:
        self.joined_encounters.append((rift_instance_id, encounter_id, participant_ref))

    async def apply_combat_result(self, **kwargs) -> dict:
        self.applied_results.append(kwargs)
        return {"applied": True}

    async def clear_run_active_encounter(self, rift_session_id: str) -> None:
        self.cleared_encounters.append(rift_session_id)

    async def clear_transition_encounter_presence(self, rift_instance_id: str, encounter_id: str) -> None:
        self.cleared_encounter_presence.append((rift_instance_id, encounter_id))


class FakeCharacterSessions:
    def __init__(self, session: dict | None = None) -> None:
        self.combat_sessions: list[tuple[int, str]] = []
        self.session = session

    async def set_combat_session(self, char_id: int, combat_id: str) -> None:
        self.combat_sessions.append((char_id, combat_id))

    async def get_session(self, char_id: int) -> dict | None:
        return self.session


@pytest.mark.asyncio
async def test_rift_encounter_service_prepares_group_from_bound_family_and_builds_combat_request() -> None:
    monster_groups = FakeMonsterGroupService()
    service = RiftEncounterService(monster_groups=monster_groups)
    runtime = _runtime()
    session = {
        "rift_session_id": "rift-run-1",
        "participant_ref": "char:7",
        "entry_context": {
            "combat_power": {
                "player_gear_score": 612,
            },
            "skills": {"skill_hunting": 1.0},
        },
    }
    prompt = RiftCombatPromptDTO(
        source="rift_transition",
        title="Шорох у повозки",
        description="Из-за борта поднимается силуэт.",
        actions=[RiftCombatPromptActionDTO(id="attack", label="В бой!", action="attack")],
        metadata={"event_scope": "transition", "to_node_id": "node-start"},
    )

    enriched = await service.enrich_combat_prompt(runtime, session=session, prompt=prompt)

    assert monster_groups.calls[0]["clan_id"] == "11111111-1111-1111-1111-111111111111"
    assert monster_groups.calls[0]["budget"] == 612
    assert monster_groups.calls[0]["tier"] == 1
    assert monster_groups.calls[0]["biome_id"] == "broken_road"
    assert monster_groups.calls[0]["loc_id"] == "rift:rift-instance-1:node-start"
    assert monster_groups.calls[0]["composition_policy"] == {
        "allowed_roles": ["minion"],
        "required_roles": [],
        "min_units": 1,
        "max_units": 3,
        "allow_repeated_members": True,
        "prefer_distinct_members": True,
    }
    assert enriched.enemies[0].name == "Дорожный налетчик"
    assert enriched.enemies[0].threat_rating is None
    assert enriched.enemies[0].intel["vitals"]["hp"] == {"current": 100, "max": 100, "label": "100/100"}
    assert enriched.metadata["monster_intel"]["level"] == 4
    assert enriched.metadata["combat"]["status"] == "ready"
    assert enriched.metadata["combat"]["battle_type"] == "rift"
    assert enriched.metadata["monster_group"]["group_id"] == "rift:encounter:1"
    request = enriched.metadata["combat"]["request"]
    assert request["source"] == "rift"
    assert request["battle_type"] == "rift"
    assert request["requested_by"] == 7
    assert request["rift_session_id"] == "rift-run-1"
    assert request["rift_instance_id"] == "rift-instance-1"
    assert request["rift_node_id"] == "node-start"
    assert request["rift_event_scope"] == "transition"
    assert request["rift_target_node_id"] == "node-start"
    assert request["location_id"] == "rift:rift-instance-1:node-start"
    assert request["participants"] == {"team_1": [7], "team_2": ["monster-1"]}
    assert request["commitments"] == {"monster:monster-1": "actor:snapshot:monster-1"}
    assert request["combat_id"].startswith("rift-")


@pytest.mark.asyncio
async def test_rift_encounter_service_uses_secondary_beast_family_for_scavenger_nodes() -> None:
    monster_groups = FakeMonsterGroupService()
    service = RiftEncounterService(monster_groups=monster_groups)
    runtime = _runtime()
    session = {
        "rift_session_id": "rift-run-1",
        "participant_ref": "char:7",
        "entry_context": {"combat_power": {"player_gear_score": 612}},
    }
    prompt = RiftCombatPromptDTO(
        source="rift_transition",
        title="Шорох у повозки",
        description="Под фургоном шевелятся мелкие силуэты.",
        actions=[RiftCombatPromptActionDTO(id="attack", label="В бой!", action="attack")],
        metadata={"event_scope": "transition", "to_node_id": "node-wagon"},
    )

    await service.enrich_combat_prompt(runtime, session=session, prompt=prompt)

    assert monster_groups.calls[0]["clan_id"] == "22222222-2222-2222-2222-222222222222"
    assert monster_groups.calls[0]["loc_id"] == "rift:rift-instance-1:node-wagon"


@pytest.mark.asyncio
async def test_rift_encounter_service_launches_real_combat_and_locks_rift_session() -> None:
    monster_groups = FakeMonsterGroupService()
    combat_creator = FakeCombatCreator()
    runtime_integration = FakeRuntimeIntegration()
    character_sessions = FakeCharacterSessions()
    service = RiftEncounterService(
        monster_groups=monster_groups,
        combat_creator=combat_creator,
        runtime=runtime_integration,
        character_sessions=character_sessions,
    )
    runtime = _runtime()
    session = {
        "rift_session_id": "rift-run-1",
        "participant_ref": "char:7",
        "entry_context": {"combat_power": {"player_gear_score": 612}},
    }
    prompt = RiftCombatPromptDTO(
        source="rift_transition",
        title="Шорох у повозки",
        description="Из-за борта поднимается силуэт.",
        actions=[RiftCombatPromptActionDTO(id="attack", label="В бой!", action="attack")],
        metadata={"event_scope": "transition", "travel_id": "trv-1", "to_node_id": "node-start"},
    )

    launched = await service.launch_combat_from_prompt(runtime, session=session, prompt=prompt)

    request = combat_creator.requests[0]
    combat_id = request["combat_id"]
    assert request["source"] == "rift"
    assert request["rift_session_id"] == "rift-run-1"
    assert request["rift_event_scope"] == "transition"
    assert request["rift_travel_id"] == "trv-1"
    assert request["rift_target_node_id"] == "node-start"
    assert runtime_integration.active_encounters == [("rift-run-1", combat_id)]
    assert runtime_integration.joined_encounters == [("rift-instance-1", combat_id, "char:7")]
    assert character_sessions.combat_sessions == [(7, combat_id)]
    assert launched.metadata["combat"]["status"] == "started"
    assert launched.metadata["combat"]["combat_id"] == combat_id


@pytest.mark.asyncio
async def test_rift_encounter_service_resolves_stale_active_encounter_before_launching_new_combat() -> None:
    monster_groups = FakeMonsterGroupService()
    combat_creator = FakeCombatCreator()
    runtime_integration = FakeRuntimeIntegration()
    character_sessions = FakeCharacterSessions(
        {"state": "rift", "sessions": {"combat_id": None, "combat_finalization_id": None}}
    )
    service = RiftEncounterService(
        monster_groups=monster_groups,
        combat_creator=combat_creator,
        runtime=runtime_integration,
        character_sessions=character_sessions,
    )
    runtime = _runtime()
    session = {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "participant_ref": "char:7",
        "active_encounter_id": "rift-old-combat",
        "active_travel": {"travel_id": "travel-1"},
        "entry_context": {"combat_power": {"player_gear_score": 612}},
    }
    prompt = RiftCombatPromptDTO(
        source="rift_transition",
        title="Шорох у повозки",
        description="Из-за борта поднимается силуэт.",
        actions=[RiftCombatPromptActionDTO(id="attack", label="В бой!", action="attack")],
        metadata={"event_scope": "transition", "travel_id": "travel-1", "to_node_id": "node-start"},
    )

    launched = await service.launch_combat_from_prompt(runtime, session=session, prompt=prompt)

    # Stale encounter is force-cleared without auto-applying a victory result.
    assert runtime_integration.applied_results == []
    assert runtime_integration.cleared_encounters == ["rift-run-1"]
    assert runtime_integration.cleared_encounter_presence == [("rift-instance-1", "rift-old-combat")]
    assert combat_creator.requests
    assert combat_creator.requests[0]["combat_id"] != "rift-old-combat"
    assert launched.metadata["combat"]["combat_id"] == combat_creator.requests[0]["combat_id"]


@pytest.mark.asyncio
async def test_rift_encounter_service_swallows_stale_encounter_clear_errors() -> None:
    """A failing clear must not propagate — new combat should still be launched."""
    monster_groups = FakeMonsterGroupService()
    combat_creator = FakeCombatCreator()

    class _BrokenRuntime(FakeRuntimeIntegration):
        async def clear_run_active_encounter(self, rift_session_id: str) -> None:
            raise RuntimeError("redis down")

    runtime_integration = _BrokenRuntime()
    character_sessions = FakeCharacterSessions(
        {"state": "rift", "sessions": {"combat_id": None, "combat_finalization_id": None}}
    )
    service = RiftEncounterService(
        monster_groups=monster_groups,
        combat_creator=combat_creator,
        runtime=runtime_integration,
        character_sessions=character_sessions,
    )
    runtime = _runtime()
    session = {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "participant_ref": "char:7",
        "active_encounter_id": "rift-old-combat",
        "active_travel": {"travel_id": "travel-1"},
        "entry_context": {"combat_power": {"player_gear_score": 612}},
    }
    prompt = RiftCombatPromptDTO(
        source="rift_transition",
        title="Шорох у повозки",
        description="Из-за борта поднимается силуэт.",
        actions=[RiftCombatPromptActionDTO(id="attack", label="В бой!", action="attack")],
        metadata={"event_scope": "transition", "travel_id": "travel-1", "to_node_id": "node-start"},
    )

    launched = await service.launch_combat_from_prompt(runtime, session=session, prompt=prompt)

    assert combat_creator.requests, "new combat should still be created despite clear failure"
    assert launched.metadata["combat"]["combat_id"] == combat_creator.requests[0]["combat_id"]


def _runtime() -> RiftZoneRuntimeDTO:
    return RiftZoneRuntimeDTO(
        rift_instance_id="rift-instance-1",
        zone_instance_id="zone-1",
        zone_canvas_key="starter",
        scale_preset_key="starter_5x5",
        assembly_preset_key="starter",
        setting={"setting_key": "starter_rift", "title": "Рваный тракт", "tier": 1},
        nodes={
            "node-start": RiftZoneCellDTO(
                node_id="node-start",
                x=2,
                y=2,
                pool_node_id="pool-start",
                node_hex="A",
                title="Сухая дорога",
                description="Стартовая точка.",
                tags=["road"],
            ),
            "node-wagon": RiftZoneCellDTO(
                node_id="node-wagon",
                x=3,
                y=2,
                pool_node_id="pool-wagon",
                node_hex="B",
                title="Тележный завал",
                description="Под фургоном шуршит мелкая падаль.",
                tags=["wagon", "debris", "cache"],
            )
        },
        cells_by_coord={"2:2": "node-start", "3:2": "node-wagon"},
        start_node_id="node-start",
        finish_node_id="node-start",
        current_node_id="node-start",
        visited_node_ids={"node-start"},
        population_context={
            "setting_key": "starter_rift",
            "biome_id": "broken_road",
            "tier": 1,
            "family_bindings": {
                "primary": {
                    "slot_id": "primary",
                    "family_id": "bandit_gang",
                    "clan_id": "11111111-1111-1111-1111-111111111111",
                    "context_hash": "ctx-primary",
                    "unique_hash": "unique-primary",
                    "source": "rift_static_bootstrap",
                },
                "secondary": {
                    "slot_id": "secondary",
                    "family_id": "rat_swarm",
                    "clan_id": "22222222-2222-2222-2222-222222222222",
                    "context_hash": "ctx-secondary",
                    "unique_hash": "unique-secondary",
                    "source": "rift_static_bootstrap",
                },
            },
        },
    )
