from __future__ import annotations

import pytest

from src.backend.features.combat.workers.tasks.victory_finalizer_task import victory_finalizer_task


class FakeCombatDataService:
    def __init__(self) -> None:
        self.winner: tuple[str, str] | None = None
        self.saved_finalization: tuple[str, dict, list[int], int] | None = None

    async def set_battle_winner(self, session_id: str, winner: str) -> None:
        self.winner = (session_id, winner)

    async def get_meta(self, session_id: str) -> dict:
        return {
            "teams": '{"team_1": ["7"], "team_2": ["wolf_1"]}',
            "battle_type": "pve",
            "location_id": "forest",
            "source": "exploration",
            "start_time": "100",
        }

    def actor_ids_from_meta(self, meta: dict) -> list[str]:
        return ["7", "wolf_1"]

    async def get_actors_batch(self, session_id: str, actor_ids: list[str]) -> dict:
        return {
            "7": {
                "meta": {
                    "name": "Hero",
                    "team": "team_1",
                    "type": "player",
                    "hp": 20,
                    "max_hp": 100,
                    "en": 8,
                    "max_en": 30,
                    "stamina": 12,
                    "max_stamina": 50,
                },
                "raw": {
                    "attributes": {
                        "strength": {"base": 8},
                        "agility": {"base": 8},
                        "endurance": {"base": 8},
                        "perception": {"base": 8},
                        "intellect": {"base": 8},
                        "memory": {"base": 8},
                        "mental": {"base": 8},
                        "projection": {"base": 8},
                        "prediction": {"base": 8},
                    }
                },
                "skills": {"skill_swords": 0.0},
                "loadout": {"layout": {"main_hand": "skill_swords"}},
                "xp_buffer": {"main_hand_hit": 1},
            }
        }

    async def get_logs_by_turn(self, session_id: str) -> dict:
        return {"1": ['{"text": "hit", "global_turn": 1}']}

    async def get_analytics(self, session_id: str) -> dict:
        return {"1:0": {"t": 1, "o": "H"}}

    async def save_finalization(self, session_id: str, payload: dict, *, char_ids: list[int], ttl: int) -> None:
        self.saved_finalization = (session_id, payload, char_ids, ttl)


class FakeCharacterSessions:
    def __init__(self) -> None:
        self.updated: list[tuple[int, str, int | None, int | None]] = []
        self.progress: list[tuple[int, dict]] = []
        self.patches: list[tuple[int, dict]] = []
        self.dirty: list[tuple[int, str, list[str]]] = []

    async def update_vital(  # noqa: A002
        self,
        char_id: int,
        vital: str,
        *,
        cur: int | None = None,
        max: int | None = None,  # noqa: A002
    ) -> None:
        self.updated.append((char_id, vital, cur, max))

    async def apply_skill_progress(self, char_id: int, rewards: dict) -> None:
        self.progress.append((char_id, rewards))

    async def patch_fields(self, char_id: int, updates: dict) -> None:
        self.patches.append((char_id, updates))

    async def mark_dirty(self, char_id: int, *, reason: str, paths: list[str]) -> None:
        self.dirty.append((char_id, reason, paths))


class FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict]] = []

    async def enqueue_job(self, name: str, payload: dict) -> None:
        self.jobs.append((name, payload))


@pytest.mark.asyncio
async def test_victory_finalizer_commits_player_vitals_to_active_session() -> None:
    data_service = FakeCombatDataService()
    character_sessions = FakeCharacterSessions()
    queue = FakeQueue()

    await victory_finalizer_task(
        {"combat_data_service": data_service, "character_sessions": character_sessions, "redis": queue},
        {"session_id": "combat-1", "winner": "team_1"},
    )

    assert data_service.winner == ("combat-1", "team_1")
    assert character_sessions.updated == [
        (7, "hp", 20, 100),
        (7, "energy", 8, 30),
        (7, "stamina", 12, 50),
    ]
    assert character_sessions.progress == [(7, {"skill_swords": 0.0016})]
    assert character_sessions.patches == [
        (
            7,
            {
                "$.sessions.combat_id": None,
                "$.sessions.combat_finalization_id": "combat-1",
                "$.state": "combat_result",
            },
        )
    ]
    assert character_sessions.dirty == [
        (
            7,
            "combat_finalization_attached",
            ["$.sessions.combat_finalization_id", "$.sessions.combat_id", "$.state"],
        )
    ]
    assert data_service.saved_finalization is not None
    session_id, finalization, char_ids, ttl = data_service.saved_finalization
    assert session_id == "combat-1"
    assert char_ids == [7]
    assert ttl == 86400
    assert finalization["actors"]["7"]["xp_buffer"] == {"main_hand_hit": 1.0}
    assert finalization["actors"]["7"]["progression"] == {"skill_swords": 0.0016}
    assert finalization["report"]["last_turn"] == 1
    assert finalization["analytics"] == {"1:0": {"t": 1, "o": "H"}}
    assert queue.jobs == [("combat_finalization_persist_task", {"combat_id": "combat-1"})]
