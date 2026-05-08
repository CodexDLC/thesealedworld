from contextlib import asynccontextmanager

import pytest

import src.backend.features.character.integrations.combat_commitment_integration as commitment_module
from src.backend.features.character.integrations import CharacterCombatCommitmentIntegration


class FakeCharacterSessions:
    def __init__(self):
        self.regenerated = []

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
                "items": {},
                "skills": {},
            }
            for char_id in char_ids
        }


class FakeCommitmentManager:
    def __init__(self):
        self.saved = {}

    async def save_commitments(self, commitments, ttl=300):
        self.saved = commitments
        return {commitment_id: commitment_id for commitment_id in commitments}


class FakeItemRepository:
    def __init__(self, session):
        self.session = session

    async def get_equipped_for_characters(self, char_ids):
        return {char_id: [] for char_id in char_ids}


class FakeEquippedItemRepository:
    def __init__(self, session):
        self.session = session

    async def get_equipped_for_characters(self, char_ids):
        return {
            7: [
                {
                    "item_id": "katana-1",
                    "base_id": "katana",
                    "item_type": "weapon",
                    "slot": "two_hand",
                    "placement": "equipped",
                    "mechanics": {
                        "power": 9,
                        "damage_spread": 0.1,
                        "related_skill": "skill_swords",
                        "triggers": ["crit.bleed_on_crit"],
                    },
                    "tags": ["katana"],
                    "metadata": {"related_skill": "skill_swords"},
                }
            ]
        }


@asynccontextmanager
async def fake_session_factory():
    yield object()


@pytest.mark.asyncio
async def test_character_combat_commitment_integration_builds_player_commitments_from_ac(monkeypatch):
    monkeypatch.setattr(commitment_module, "ItemInstanceRepository", FakeItemRepository)
    commitment_manager = FakeCommitmentManager()
    character_sessions = FakeCharacterSessions()
    result = await CharacterCombatCommitmentIntegration(
        character_sessions=character_sessions,
        commitment_manager=commitment_manager,
        session_factory=fake_session_factory,
    ).prepare_commitments(
        scope_id="combat-1",
        player_ids=[7],
        monster_ids=[],
        ttl=600,
    )

    commitment = commitment_manager.saved["combat-1:player:7"]

    assert result.commitments == {"combat-1:player:7": "combat-1:player:7"}
    assert result.failed_players == []
    assert character_sessions.regenerated == [7]
    assert commitment["meta"]["actor_id"] == 7
    assert commitment["status"]["hp"]["max"] == 64
    assert commitment["combat"]["math_model"]["modifiers"]


@pytest.mark.asyncio
async def test_character_combat_commitment_materializes_equipped_items_from_items_store(monkeypatch):
    monkeypatch.setattr(commitment_module, "ItemInstanceRepository", FakeEquippedItemRepository)
    commitment_manager = FakeCommitmentManager()

    await CharacterCombatCommitmentIntegration(
        character_sessions=FakeCharacterSessions(),
        commitment_manager=commitment_manager,
        session_factory=fake_session_factory,
    ).prepare_commitments(
        scope_id="combat-1",
        player_ids=[7],
        monster_ids=[],
        ttl=600,
    )

    commitment = commitment_manager.saved["combat-1:player:7"]

    assert commitment["combat"]["math_model"]["modifiers"]["main_hand_damage_base"]["base"] == 9.0
    assert commitment["combat"]["loadout"]["equipment_layout"] == {"two_hand": "katana-1"}
    assert commitment["combat"]["loadout"]["hand_usage"] == {"main_hand": "two_hand"}
