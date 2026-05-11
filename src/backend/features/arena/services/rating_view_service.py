from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.arena.runtime.league_resolver import LeagueResolver
from src.backend.features.arena.runtime.rules.leagues import DEFAULT_LEAGUES

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.arena.services.rating_service import RatingService
    from src.backend.features.arena.services.season_service import SeasonService


class ArenaRatingViewService:
    def __init__(
        self,
        *,
        seasons: SeasonService,
        ratings: RatingService,
        db_session: AsyncSession | None = None,
    ) -> None:
        self.seasons = seasons
        self.ratings = ratings
        self.db_session = db_session

    async def player_metadata(self, *, char_id: int, mode_size: int = 1) -> dict[str, Any]:
        season = await self.seasons.ensure_current_season()
        snapshot = await self.ratings.get_player_rating(char_id=char_id, mode_size=mode_size, season_id=season.id)
        if self.db_session is not None:
            await self.db_session.commit()
        league = LeagueResolver(DEFAULT_LEAGUES).resolve(snapshot.rating)
        return {
            "season_id": season.id,
            "season_name": season.name,
            "season_status": season.status,
            "rating": snapshot.rating,
            "peak_rating": snapshot.peak_rating,
            "rank": snapshot.rating,
            "tier": snapshot.league_tier,
            "league_tier": snapshot.league_tier,
            "league_code": league.code,
            "league_name": league.name,
            "wins": snapshot.wins,
            "losses": snapshot.losses,
            "draws": snapshot.draws,
            "matches_played": snapshot.matches_played,
            "placement_left": snapshot.placement_left,
        }
