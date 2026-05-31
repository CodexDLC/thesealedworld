from __future__ import annotations

import json

import pytest

from src.backend.features.combat.services.loot_preorder_service import CombatLootPreorderService
from src.backend.features.combat.services.post_battle_router import CombatPostBattleRouter
from src.shared.schemas.loot import CorpseDTO, LootItemDTO


class FakeLootOrders:
    def __init__(self) -> None:
        self.orders: list[dict] = []

    async def order_hidden_corpses(self, **kwargs) -> None:
        self.orders.append(kwargs)


class FakeRedisClient:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    async def get(self, key: str):
        return self.values.get(key)


class FakeRedisService:
    def __init__(self, values: dict[str, str]) -> None:
        self.redis_client = FakeRedisClient(values)


class FakeCharacterSessions:
    async def get_session(self, char_id: int) -> dict:
        return {
            "sessions": {"death_run_id": "run-1", "death_corpse_id": "player-corpse"},
            "risk": {"carried_item_count": 1, "carried_resource_count": 1},
            "pending_progress": {"free_xp": 10, "skills": {"swords": 2}},
        }


class FakeLootIntegration:
    activated: list[tuple[list[str], list[int], str]] = []
    corpses: dict[str, CorpseDTO] = {}

    def __init__(self, manager, **kwargs) -> None:
        self.manager = manager

    async def activate_corpses(self, corpse_ids: list[str], char_ids: list[int], location_id: str) -> None:
        self.activated.append((corpse_ids, char_ids, location_id))

    async def get_corpse(self, corpse_id: str) -> CorpseDTO | None:
        return self.corpses.get(corpse_id)


@pytest.mark.asyncio
async def test_loot_preorder_enqueues_only_non_arena_monsters() -> None:
    orders = FakeLootOrders()
    service = CombatLootPreorderService(orders)

    await service.enqueue(
        combat_id="combat-1",
        battle_type="pve",
        location_id="forest",
        actors={
            "7": {"meta": {"type": "player"}},
            "wolf_1": {"meta": {"type": "monster", "id": "wolf_1"}},
        },
    )

    assert orders.orders == [
        {
            "session_id": "combat-1",
            "battle_type": "pve",
            "location_id": "forest",
            "actors": [{"meta": {"type": "monster", "id": "wolf_1"}, "actor_id": "wolf_1"}],
        }
    ]


@pytest.mark.asyncio
async def test_post_battle_router_activates_only_dead_monster_corpses(monkeypatch) -> None:
    FakeLootIntegration.activated = []
    FakeLootIntegration.corpses = {
        "corpse-dead": CorpseDTO(
            id="corpse-dead",
            monster_name="Wolf",
            is_visible=True,
            items=[LootItemDTO(template_id="fang", name="Fang")],
        ),
        "corpse-alive": CorpseDTO(
            id="corpse-alive",
            monster_name="Bear",
            is_visible=False,
            items=[LootItemDTO(template_id="claw", name="Claw")],
        ),
    }
    monkeypatch.setattr(
        "src.backend.features.combat.services.post_battle_router.LootIntegration",
        FakeLootIntegration,
    )

    finalization = {
        "combat_id": "combat-1",
        "winner_team": "team_1",
        "participant_char_ids": [7],
        "meta": {"battle_type": "pve", "location_id": "forest"},
        "actors": {
            "7": {"char_id": 7, "team": "team_1", "is_dead": False},
            "wolf_1": {"char_id": None, "team": "team_2", "is_dead": True},
            "bear_1": {"char_id": None, "team": "team_2", "is_dead": False},
        },
    }
    ctx = {
        "redis_service": FakeRedisService(
            {"loot:pending:combat-1": json.dumps({"wolf_1": "corpse-dead", "bear_1": "corpse-alive"})}
        )
    }

    outcomes = await CombatPostBattleRouter().build_outcomes(ctx, finalization)

    assert FakeLootIntegration.activated == [(["corpse-dead"], [7], "forest")]
    assert outcomes[7].target_state == "loot"
    assert outcomes[7].corpse_ids == ["corpse-dead"]


@pytest.mark.asyncio
async def test_post_battle_router_routes_empty_corpse_to_loot_for_future_gathering(monkeypatch) -> None:
    FakeLootIntegration.activated = []
    FakeLootIntegration.corpses = {
        "corpse-empty": CorpseDTO(
            id="corpse-empty",
            monster_name="Scavenger",
            is_visible=True,
            items=[],
        )
    }
    monkeypatch.setattr(
        "src.backend.features.combat.services.post_battle_router.LootIntegration",
        FakeLootIntegration,
    )

    finalization = {
        "combat_id": "combat-empty-corpse",
        "winner_team": "team_1",
        "participant_char_ids": [7],
        "meta": {"battle_type": "rift", "rift_session_id": "rift-run-1", "location_id": "rift:node"},
        "actors": {
            "7": {"char_id": 7, "team": "team_1", "is_dead": False},
            "scavenger_1": {"char_id": None, "team": "team_2", "is_dead": True},
        },
    }
    ctx = {
        "redis_service": FakeRedisService(
            {"loot:pending:combat-empty-corpse": json.dumps({"scavenger_1": "corpse-empty"})}
        )
    }

    outcomes = await CombatPostBattleRouter().build_outcomes(ctx, finalization)

    assert FakeLootIntegration.activated == [(["corpse-empty"], [7], "rift:node")]
    assert outcomes[7].target_state == "loot"
    assert outcomes[7].return_state == "rift"
    assert outcomes[7].corpse_ids == ["corpse-empty"]
    assert outcomes[7].loot_context["corpses"] == [
        {
            "corpse_id": "corpse-empty",
            "corpse_type": "monster",
            "items": [],
            "name": "Scavenger",
        }
    ]


@pytest.mark.asyncio
async def test_post_battle_router_routes_dead_player_to_death_even_with_monster_corpse(monkeypatch) -> None:
    FakeLootIntegration.activated = []
    FakeLootIntegration.corpses = {
        "corpse-dead": CorpseDTO(
            id="corpse-dead",
            monster_name="Wolf",
            is_visible=True,
            items=[LootItemDTO(template_id="fang", name="Fang")],
        ),
        "player-corpse": CorpseDTO(
            id="player-corpse",
            monster_name="Player remains",
            corpse_type="player",
            is_visible=True,
            locked_to=[7],
            items=[LootItemDTO(template_id="coin_copper", name="Copper", amount=3, is_resource=True)],
        ),
    }
    monkeypatch.setattr(
        "src.backend.features.combat.services.post_battle_router.LootIntegration",
        FakeLootIntegration,
    )

    finalization = {
        "combat_id": "combat-2",
        "winner_team": "team_2",
        "participant_char_ids": [7],
        "meta": {"battle_type": "pve", "location_id": "forest"},
        "actors": {
            "7": {"char_id": 7, "team": "team_1", "is_dead": True},
            "wolf_1": {"char_id": None, "team": "team_2", "is_dead": True},
        },
    }
    ctx = {
        "redis_service": FakeRedisService({"loot:pending:combat-2": json.dumps({"wolf_1": "corpse-dead"})}),
        "character_sessions": FakeCharacterSessions(),
    }

    outcomes = await CombatPostBattleRouter().build_outcomes(ctx, finalization)

    assert FakeLootIntegration.activated == [(["corpse-dead"], [], "forest")]
    assert outcomes[7].target_state == "death"
    assert outcomes[7].death_summary["corpse_id"] == "player-corpse"
    assert outcomes[7].death_summary["dropped_items"][0]["template_id"] == "coin_copper"


@pytest.mark.asyncio
async def test_post_battle_router_adds_rift_death_policy_to_dead_player() -> None:
    finalization = {
        "combat_id": "combat-rift-death",
        "winner_team": "team_2",
        "participant_char_ids": [7],
        "meta": {
            "battle_type": "rift",
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
            "rift_entrance_seals_on_entry": True,
        },
        "actors": {
            "7": {"char_id": 7, "team": "team_1", "is_dead": True},
        },
    }
    ctx = {"character_sessions": FakeCharacterSessions()}

    outcomes = await CombatPostBattleRouter().build_outcomes(ctx, finalization)

    assert outcomes[7].target_state == "death"
    assert outcomes[7].death_summary["rift"] == {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "rift-instance-1",
        "entrance_seals_on_entry": True,
        "death_policy": "sealed_access_lost",
    }


@pytest.mark.asyncio
async def test_post_battle_router_routes_rift_combat_back_to_rift_when_no_loot(monkeypatch) -> None:
    FakeLootIntegration.activated = []
    FakeLootIntegration.corpses = {}
    monkeypatch.setattr(
        "src.backend.features.combat.services.post_battle_router.LootIntegration",
        FakeLootIntegration,
    )

    finalization = {
        "combat_id": "combat-rift-1",
        "winner_team": "team_1",
        "participant_char_ids": [7],
        "meta": {"battle_type": "rift", "rift_session_id": "rift-run-1", "location_id": ""},
        "actors": {
            "7": {"char_id": 7, "team": "team_1", "is_dead": False},
            "scavenger_1": {"char_id": None, "team": "team_2", "is_dead": True},
        },
    }
    ctx = {"redis_service": FakeRedisService({"loot:pending:combat-rift-1": json.dumps({})})}

    outcomes = await CombatPostBattleRouter().build_outcomes(ctx, finalization)

    assert outcomes[7].target_state == "rift"
    assert outcomes[7].loot_context == {
        "rift_session_id": "rift-run-1",
        "rift_instance_id": "",
        "rift_node_id": "",
        "rift_event_scope": "",
        "rift_travel_id": "",
        "rift_event_key": "",
        "rift_target_node_id": "",
        "rift_location_id": "",
    }


@pytest.mark.asyncio
async def test_post_battle_router_routes_rift_loot_to_loot_with_rift_return_context(monkeypatch) -> None:
    FakeLootIntegration.activated = []
    FakeLootIntegration.corpses = {
        "corpse-rift": CorpseDTO(
            id="corpse-rift",
            monster_name="Scavenger",
            is_visible=True,
            items=[LootItemDTO(template_id="rusted_hook", name="Rusted hook")],
        )
    }
    monkeypatch.setattr(
        "src.backend.features.combat.services.post_battle_router.LootIntegration",
        FakeLootIntegration,
    )

    finalization = {
        "combat_id": "combat-rift-loot",
        "winner_team": "team_1",
        "participant_char_ids": [7],
        "meta": {
            "battle_type": "rift",
            "rift_session_id": "rift-run-1",
            "rift_instance_id": "rift-instance-1",
            "rift_node_id": "node-road",
            "location_id": "rift:rift-instance-1:node-road",
        },
        "actors": {
            "7": {"char_id": 7, "team": "team_1", "is_dead": False},
            "scavenger_1": {"char_id": None, "team": "team_2", "is_dead": True},
        },
    }
    ctx = {"redis_service": FakeRedisService({"loot:pending:combat-rift-loot": json.dumps({"scavenger_1": "corpse-rift"})})}

    outcomes = await CombatPostBattleRouter().build_outcomes(ctx, finalization)

    assert FakeLootIntegration.activated == [(["corpse-rift"], [7], "rift:rift-instance-1:node-road")]
    assert outcomes[7].target_state == "loot"
    assert outcomes[7].return_state == "rift"
    assert outcomes[7].loot_context["return_state"] == "rift"
    assert outcomes[7].loot_context["rift_session_id"] == "rift-run-1"
    assert outcomes[7].loot_context["rift_instance_id"] == "rift-instance-1"
    assert outcomes[7].loot_context["rift_node_id"] == "node-road"
