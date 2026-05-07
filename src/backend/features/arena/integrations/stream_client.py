from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.backend.features.character.events import CharacterEvents

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.infrastructure.arena.schemas.session import ArenaCombatSessionSchema


MATCH_COMPLETED = "combat.match_completed"
RATING_UPDATED = "arena.rating_updated"
SEASON_ENDED = "arena.season_ended"
TEAM_CHANGED = "arena.team_changed"
COMBAT_SESSION_REQUESTED = "combat.session_requested"


class ArenaStreamClient:
    COMMITMENT_TIMEOUT_SECONDS = 5.0
    GEAR_SCORE_TIMEOUT_SECONDS = 5.0

    def __init__(self, events: GameEventProducer) -> None:
        self.events = events

    async def request_combat_session(self, request: ArenaCombatSessionSchema) -> None:
        await self.events.publish(
            COMBAT_SESSION_REQUESTED,
            request.model_dump(mode="json"),
            correlation_id=request.arena_session_id,
        )

    async def request_combat_commitment(self, *, request_id: str, char_ids: list[int], ttl: int) -> dict[str, str]:
        response = await self.events.request(
            CharacterEvents.COMBAT_COMMITMENTS_REQUESTED,
            {
                "scope_id": request_id,
                "player_ids": json.dumps(char_ids),
                "monster_ids": "[]",
                "ttl": ttl,
                "include": json.dumps(["combat", "status", "runtime", "source"]),
            },
            timeout=self.COMMITMENT_TIMEOUT_SECONDS,
        )
        if not isinstance(response, dict) or response.get("status") not in ("ok", "partial"):
            return {}
        commitments = _json_dict(response.get("commitments"))
        return {str(key): str(value) for key, value in commitments.items() if value}

    async def request_gear_scores(self, char_ids: list[int]) -> dict[int, int]:
        response = await self.events.request(
            CharacterEvents.GEAR_SCORE_RECALCULATE_REQUESTED,
            {"char_ids": json.dumps(char_ids)},
            timeout=self.GEAR_SCORE_TIMEOUT_SECONDS,
        )
        if not isinstance(response, dict) or response.get("status") not in ("ok", "partial"):
            return {}
        gear_scores = _json_dict(response.get("gear_scores"))
        return {int(char_id): int(score) for char_id, score in gear_scores.items()}

    async def publish_rating_updated(
        self,
        *,
        entity_type: str,
        entity_id: int,
        mode_size: int,
        season_id: int,
        rating_before: int,
        rating_after: int,
        league_before: int,
        league_after: int,
        match_id: int,
    ) -> None:
        await self.events.publish(
            RATING_UPDATED,
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "mode_size": mode_size,
                "season_id": season_id,
                "rating_before": rating_before,
                "rating_after": rating_after,
                "league_before": league_before,
                "league_after": league_after,
                "match_id": match_id,
            },
        )

    async def publish_season_ended(self, *, season_id: int, ended_at: str) -> None:
        await self.events.publish(SEASON_ENDED, {"season_id": season_id, "ended_at": ended_at})

    async def publish_team_changed(self, *, team_id: int, kind: str) -> None:
        await self.events.publish(TEAM_CHANGED, {"team_id": team_id, "kind": kind})


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, dict) else {}
