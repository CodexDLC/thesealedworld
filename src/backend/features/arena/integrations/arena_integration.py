from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.character.runtime.gear_score import CharacterGearScoreCalculator

if TYPE_CHECKING:
    from src.backend.features.arena.integrations.stream_client import ArenaStreamClient
    from src.backend.features.character.managers import CharacterSessionManager
    from src.backend.infrastructure.arena.managers import ArenaSessionManager


class ArenaIntegration:
    """Feature-facing facade for the new ranking slice.

    This is intentionally not wired into the existing ArenaService yet. The final
    app connection happens after the rating/team/season services are complete.
    """

    def __init__(
        self,
        *,
        session_manager: ArenaSessionManager,
        stream_client: ArenaStreamClient,
        character_sessions: CharacterSessionManager | None = None,
        gear_score_calculator: CharacterGearScoreCalculator | None = None,
    ) -> None:
        self.session_manager = session_manager
        self.stream_client = stream_client
        self.character_sessions = character_sessions
        self.gear_score_calculator = gear_score_calculator or CharacterGearScoreCalculator()

    async def fetch_gear_score(self, char_id: int) -> int:
        if self.character_sessions is not None:
            session = await self.character_sessions.get_session(char_id)
            if isinstance(session, dict):
                metrics = session.get("metrics") if isinstance(session.get("metrics"), dict) else {}
                cached = metrics.get("gear_score")
                if cached is not None:
                    return max(0, int(cached))
                score = self.gear_score_calculator.calculate_from_active_character(session)
                await self.character_sessions.patch_fields(char_id, {"$.metrics.gear_score": score})
                return score

        scores = await self.stream_client.request_gear_scores([char_id])
        if char_id not in scores:
            raise RuntimeError(f"character gear score unavailable: char_id={char_id}")
        return scores[char_id]

    async def fetch_gear_scores(self, char_ids: list[int]) -> dict[int, int]:
        if self.character_sessions is None:
            return await self.stream_client.request_gear_scores(char_ids)

        scores: dict[int, int] = {}
        sessions = await self.character_sessions.get_sessions_batch(char_ids)
        for char_id, session in sessions.items():
            if not isinstance(session, dict):
                continue
            metrics = session.get("metrics") if isinstance(session.get("metrics"), dict) else {}
            cached = metrics.get("gear_score")
            if cached is not None:
                scores[char_id] = max(0, int(cached))
                continue
            score = self.gear_score_calculator.calculate_from_active_character(session)
            await self.character_sessions.patch_fields(char_id, {"$.metrics.gear_score": score})
            scores[char_id] = score

        missing = [char_id for char_id in char_ids if char_id not in scores]
        if missing:
            scores.update(await self.stream_client.request_gear_scores(missing))
        return scores
