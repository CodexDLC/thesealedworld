from __future__ import annotations

import pytest

from src.backend.features.combat.workers.tasks.victory_finalizer_task import victory_finalizer_task


class FakeCombatDataService:
    def __init__(self) -> None:
        self.winner: tuple[str, str] | None = None

    async def set_battle_winner(self, session_id: str, winner: str) -> None:
        self.winner = (session_id, winner)

    async def get_meta(self, session_id: str) -> dict:
        return {"teams": '{"team_1": ["7"], "team_2": ["wolf_1"]}'}

    def actor_ids_from_meta(self, meta: dict) -> list[str]:
        return ["7", "wolf_1"]

    async def get_actors_batch(self, session_id: str, actor_ids: list[str]) -> dict:
        return {
            "7": {
                "meta": {
                    "hp": 20,
                    "max_hp": 100,
                    "en": 8,
                    "max_en": 30,
                    "stamina": 12,
                    "max_stamina": 50,
                }
            }
        }


class FakeCharacterSessions:
    def __init__(self) -> None:
        self.updated: list[tuple[int, str, int | None, int | None]] = []

    async def update_vital(  # noqa: A002
        self,
        char_id: int,
        vital: str,
        *,
        cur: int | None = None,
        max: int | None = None,  # noqa: A002
    ) -> None:
        self.updated.append((char_id, vital, cur, max))


@pytest.mark.asyncio
async def test_victory_finalizer_commits_player_vitals_to_active_session() -> None:
    data_service = FakeCombatDataService()
    character_sessions = FakeCharacterSessions()

    await victory_finalizer_task(
        {"combat_data_service": data_service, "character_sessions": character_sessions},
        {"session_id": "combat-1", "winner": "team_1"},
    )

    assert data_service.winner == ("combat-1", "team_1")
    assert character_sessions.updated == [
        (7, "hp", 20, 100),
        (7, "energy", 8, 30),
        (7, "stamina", 12, 50),
    ]
