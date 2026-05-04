from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.infrastructure.actor_state import CharacterSessionManager
    from src.backend.infrastructure.world.location_store import WorldLocationStore

log = logging.getLogger(__name__)


class ExplorationSystemIntegrator:
    """
    Integrates Exploration logic with Infrastructure (Redis, DB).
    Provides a unified data access layer for the feature.

    Combines player state (CharacterSessionManager) with world state (WorldLocationStore).
    """

    def __init__(
        self,
        character_sessions: CharacterSessionManager,
        world_store: WorldLocationStore,
    ) -> None:
        self.character_sessions = character_sessions
        self.world_store = world_store

    async def get_player_location_id(self, char_id: int) -> str | None:
        """Fetch current location ID from character session."""
        loc = await self.character_sessions.get_location(char_id)
        if loc and loc.get("current"):
            return loc["current"]
        return None

    async def get_location_data(self, loc_id: str) -> dict[str, Any] | None:
        """Fetch location metadata (exits, flags, etc.) from World store."""
        return await self.world_store.get_location(loc_id)

    async def move_player(self, char_id: int, from_loc: str | None, to_loc: str) -> bool:
        """
        Moves player between locations and updates Redis state.
        Handles both world-level player sets and actor-level location field.
        """
        if not await self.world_store.location_exists(to_loc):
            log.warning("ExplorationIntegrator | move_failed: target_not_found to=%s", to_loc)
            return False

        # 1. Update World State (player sets in locations)
        if from_loc:
            await self.world_store.remove_player(from_loc, char_id)
        await self.world_store.add_player(to_loc, char_id)

        # 2. Update Actor State (RedisJSON ac: key)
        await self.character_sessions.set_location(char_id, to_loc, prev=from_loc)

        log.info("ExplorationIntegrator | move_success: char_id=%s from=%s to=%s", char_id, from_loc, to_loc)
        return True

    async def set_world_theme(self, char_id: int, world_theme: dict[str, Any]) -> None:
        await self.character_sessions.set_world_theme(char_id, world_theme)

    async def get_actor_skills(self, char_id: int) -> dict[str, float]:
        """Fetch all character skills."""
        skills = await self.character_sessions.get_skills(char_id)
        return skills or {}

    async def get_players_count(self, loc_id: str, exclude_char_id: int | None = None) -> int:
        """Count players in a location, optionally excluding one."""
        players = await self.world_store.get_players(loc_id)
        if exclude_char_id is not None:
            players.discard(str(exclude_char_id))
        return len(players)

    async def get_battles(self, loc_id: str) -> dict[str, str]:
        """Fetch active battles in a location."""
        return await self.world_store.get_battles(loc_id)
