from contextlib import asynccontextmanager
from typing import Any, Literal

import pytest

from src.backend.features.character.integrations import CharacterCombatCommitmentIntegration


class FakeCharacterSessions:
    def __init__(self, items: dict[str, Any] | None = None):
        self.regenerated = []
        self.items = items or {}

    async def apply_vitals_regen(self, char_id):
        self.regenerated.append(char_id)
        return {
            "hp": {"cur": 64, "max": 64},
            "energy": {"cur": 26, "max": 26},
            "stamina": {"cur": 80, "max": 80},
        }

    async def get_sessions_batch(self, char_ids):
        return {
            char_id: {
                "char_id": char_id,
                "user_id": "00000000-0000-0000-0000-000000000001",
                "bio": {"name": f"Hero {char_id}"},
                "vitals": {"hp": {"cur": 64, "max": 64}, "energy": {"cur": 26, "max": 26}},
                "attributes": {"strength": 15, "agility": 9},
                "items": self.items,
                "skills": {},
            }
            for char_id in char_ids
        }


class FakeCommitmentManager:
    def __init__(self):
        self.saved = {}

    @staticmethod
    def source_ref(actor_type, source_id):
        return f"{actor_type}:{source_id}"

    @staticmethod
    def actor_uuid(actor_type: Literal["player", "monster"], source_id: int | str, scope_id: str | None = None) -> str:
        if scope_id:
            return f"actor:{scope_id}:{actor_type}:{source_id}"
        return f"actor:snapshot:{actor_type}:{source_id}"

    async def save_snapshots(self, snapshots: dict[str, dict[str, Any]], ttl: int = 300):
        del ttl
        self.saved.update(snapshots)
        return {actor_id: actor_id for actor_id in snapshots}


@asynccontextmanager
async def fake_session_factory():
    yield object()


@asynccontextmanager
async def player_commitment_must_not_open_db():
    raise AssertionError("player combat commitments must not read item state from DB")
    yield


@pytest.mark.asyncio
async def test_character_combat_commitment_integration_builds_player_commitments_from_ac():
    commitment_manager = FakeCommitmentManager()
    character_sessions = FakeCharacterSessions()
    result = await CharacterCombatCommitmentIntegration(
        character_sessions=character_sessions,
        commitment_manager=commitment_manager,
        session_factory=fake_session_factory,
    ).prepare_commitments(
        player_ids=[7],
        monster_ids=[],
        ttl=600,
    )

    actor_id = commitment_manager.actor_uuid("player", 7)
    commitment = commitment_manager.saved[actor_id]

    assert result.commitments == {"player:7": actor_id}
    assert result.failed_players == []
    assert character_sessions.regenerated == [7]
    assert commitment["meta"]["actor_id"] == 7
    assert commitment["status"]["hp"]["max"] == 64
    assert commitment["combat"]["math_model"]["modifiers"]


@pytest.mark.asyncio
async def test_character_combat_commitment_uses_ac_items_without_player_db_lookup():
    commitment_manager = FakeCommitmentManager()
    character_sessions = FakeCharacterSessions(
        items={
            "layout": {"equipment": {"two_hand": "katana-1"}},
            "by_id": {
                "katana-1": {
                    "item_id": "katana-1",
                    "base_id": "katana",
                    "item_type": "weapon",
                    "slot": "two_hand",
                    "placement": "equipped",
                    "mechanics": {
                        "power": 9,
                        "damage_spread": 0.1,
                        "related_skill": "skill_swords",
                        "triggers": ["crit.weapon_precision_crit"],
                    },
                    "tags": ["katana"],
                    "metadata": {"related_skill": "skill_swords"},
                },
            },
        }
    )

    await CharacterCombatCommitmentIntegration(
        character_sessions=character_sessions,
        commitment_manager=commitment_manager,
        session_factory=player_commitment_must_not_open_db,
    ).prepare_commitments(
        player_ids=[7],
        monster_ids=[],
        ttl=600,
    )

    actor_id = commitment_manager.actor_uuid("player", 7)
    commitment = commitment_manager.saved[actor_id]

    assert commitment["combat"]["math_model"]["modifiers"]["main_hand_damage_base"]["base"] == 9.0
    assert commitment["combat"]["loadout"]["equipment_layout"] == {"two_hand": "katana-1"}
    assert commitment["combat"]["loadout"]["hand_usage"] == {"main_hand": "two_hand"}
