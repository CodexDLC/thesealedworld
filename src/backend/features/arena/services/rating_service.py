from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.backend.features.arena.dto.rating import MatchResultDTO, MatchTeamDTO, RatingSnapshotDTO
from src.backend.features.arena.runtime.league_resolver import LeagueResolver
from src.backend.features.arena.runtime.rating import RatingCalculator, RatingTeamInput
from src.backend.features.arena.runtime.rules.elo import DEFAULT_RATING
from src.backend.features.arena.runtime.rules.leagues import DEFAULT_LEAGUES, LeagueRule
from src.backend.infrastructure.arena.models import ArenaMatch

if TYPE_CHECKING:
    import datetime as dt

    from src.backend.features.arena.integrations.stream_client import ArenaStreamClient
    from src.backend.infrastructure.arena.models import ArenaRating
    from src.backend.infrastructure.arena.repositories import (
        ArenaLeagueRepository,
        ArenaMatchRepository,
        ArenaRatingRepository,
    )


@dataclass(frozen=True, slots=True)
class _RowUpdate:
    row: ArenaRating
    before_rating: int
    before_league: int
    after_rating: int
    after_league: int


class RatingService:
    def __init__(
        self,
        *,
        ratings: ArenaRatingRepository,
        matches: ArenaMatchRepository,
        leagues: ArenaLeagueRepository,
        stream_client: ArenaStreamClient | None = None,
        calculator: RatingCalculator | None = None,
    ) -> None:
        self.ratings = ratings
        self.matches = matches
        self.leagues = leagues
        self.stream_client = stream_client
        self.calculator = calculator or RatingCalculator()

    async def get_player_rating(self, *, char_id: int, mode_size: int, season_id: int) -> RatingSnapshotDTO:
        row = await self.ratings.ensure(
            entity_type="character",
            entity_id=char_id,
            mode_size=mode_size,
            season_id=season_id,
        )
        return self._snapshot(row)

    async def get_leaderboard(
        self,
        *,
        season_id: int,
        mode_size: int,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RatingSnapshotDTO]:
        rows = await self.ratings.leaderboard(
            season_id=season_id,
            mode_size=mode_size,
            entity_type=entity_type,
            limit=limit,
            offset=offset,
        )
        return [self._snapshot(row) for row in rows]

    async def apply_match_result(self, result: MatchResultDTO) -> ArenaMatch:
        resolver = await self._league_resolver(result.season_id)
        team_a_entity = await self._ensure_entity_row(result.team_a, result.mode_size, result.season_id, resolver)
        team_b_entity = await self._ensure_entity_row(result.team_b, result.mode_size, result.season_id, resolver)
        team_a_member_rows = await self._ensure_member_rows(result.team_a, result.mode_size, result.season_id, resolver)
        team_b_member_rows = await self._ensure_member_rows(result.team_b, result.mode_size, result.season_id, resolver)

        rating_a = _mean_rating(team_a_member_rows or [team_a_entity])
        rating_b = _mean_rating(team_b_member_rows or [team_b_entity])
        delta_a, delta_b = self.calculator.compute_match_deltas(
            RatingTeamInput(
                rating=rating_a,
                gear_score=result.team_a.gs_locked,
                in_placement=team_a_entity.placement_left > 0,
            ),
            RatingTeamInput(
                rating=rating_b,
                gear_score=result.team_b.gs_locked,
                in_placement=team_b_entity.placement_left > 0,
            ),
            result.winner,
        )

        updates = []
        updates.extend(
            await self._apply_team_delta(
                team_a_entity,
                team_a_member_rows,
                delta_a.delta,
                delta_a.score,
                resolver,
                played_at=result.completed_at,
            )
        )
        updates.extend(
            await self._apply_team_delta(
                team_b_entity,
                team_b_member_rows,
                delta_b.delta,
                delta_b.score,
                resolver,
                played_at=result.completed_at,
            )
        )

        match = await self.matches.create(
            ArenaMatch(
                combat_id=result.combat_id,
                arena_session_id=result.arena_session_id,
                mode=result.mode,
                mode_size=result.mode_size,
                season_id=result.season_id,
                team_a_entity_type=result.team_a.entity_type,
                team_a_entity_id=result.team_a.entity_id,
                team_b_entity_type=result.team_b.entity_type,
                team_b_entity_id=result.team_b.entity_id,
                team_a_member_ids=result.team_a.member_ids,
                team_b_member_ids=result.team_b.member_ids,
                team_a_gs_locked=result.team_a.gs_locked,
                team_b_gs_locked=result.team_b.gs_locked,
                team_a_rating_before=rating_a,
                team_a_rating_after=rating_a + delta_a.delta,
                team_b_rating_before=rating_b,
                team_b_rating_after=rating_b + delta_b.delta,
                winner=result.winner,
                created_at=result.created_at,
                completed_at=result.completed_at,
            )
        )
        if self.stream_client is not None:
            for update in updates:
                await self.stream_client.publish_rating_updated(
                    entity_type=update.row.entity_type,
                    entity_id=update.row.entity_id,
                    mode_size=update.row.mode_size,
                    season_id=update.row.season_id,
                    rating_before=update.before_rating,
                    rating_after=update.after_rating,
                    league_before=update.before_league,
                    league_after=update.after_league,
                    match_id=match.id,
                )
        return match

    async def _ensure_entity_row(
        self,
        team: MatchTeamDTO,
        mode_size: int,
        season_id: int,
        resolver: LeagueResolver,
    ) -> ArenaRating:
        league = resolver.resolve(DEFAULT_RATING)
        return await self.ratings.ensure(
            entity_type=team.entity_type,
            entity_id=team.entity_id,
            mode_size=mode_size,
            season_id=season_id,
            league_tier=league.tier,
        )

    async def _ensure_member_rows(
        self,
        team: MatchTeamDTO,
        mode_size: int,
        season_id: int,
        resolver: LeagueResolver,
    ) -> list[ArenaRating]:
        league = resolver.resolve(DEFAULT_RATING)
        rows = []
        for char_id in team.member_ids:
            rows.append(
                await self.ratings.ensure(
                    entity_type="character",
                    entity_id=char_id,
                    mode_size=mode_size,
                    season_id=season_id,
                    league_tier=league.tier,
                )
            )
        return rows

    async def _apply_team_delta(
        self,
        entity_row: ArenaRating,
        member_rows: list[ArenaRating],
        delta: int,
        score: float,
        resolver: LeagueResolver,
        played_at: dt.datetime,
    ) -> list[_RowUpdate]:
        rows = _dedupe_rows([entity_row, *member_rows])
        updates = []
        for row in rows:
            before_rating = row.rating
            before_league = row.league_tier
            floor = resolver.floor_for_tier(row.league_tier)
            after_rating = max(floor, before_rating + delta)
            after_league = resolver.resolve(after_rating).tier
            await self.ratings.record_result(
                row,
                rating_after=after_rating,
                league_tier=after_league,
                score=score,
                played_at=played_at,
            )
            updates.append(
                _RowUpdate(
                    row=row,
                    before_rating=before_rating,
                    before_league=before_league,
                    after_rating=after_rating,
                    after_league=after_league,
                )
            )
        return updates

    async def _league_resolver(self, season_id: int) -> LeagueResolver:
        rows = await self.leagues.list_for_season(season_id)
        if not rows:
            return LeagueResolver(DEFAULT_LEAGUES)
        return LeagueResolver(
            [
                LeagueRule(
                    tier=row.tier,
                    code=row.code,
                    name=row.name,
                    min_rating=row.min_rating,
                    max_rating=row.max_rating,
                )
                for row in rows
                if row.season_id in (None, season_id)
            ]
        )

    @staticmethod
    def _snapshot(row: ArenaRating) -> RatingSnapshotDTO:
        return RatingSnapshotDTO(
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            mode_size=row.mode_size,
            season_id=row.season_id,
            rating=row.rating,
            peak_rating=row.peak_rating,
            wins=row.wins,
            losses=row.losses,
            draws=row.draws,
            league_tier=row.league_tier,
            matches_played=row.matches_played,
            placement_left=row.placement_left,
        )


def _mean_rating(rows: list[ArenaRating]) -> int:
    return round(sum(row.rating for row in rows) / len(rows))


def _dedupe_rows(rows: list[ArenaRating]) -> list[ArenaRating]:
    seen = set()
    deduped = []
    for row in rows:
        key = (row.entity_type, row.entity_id, row.mode_size, row.season_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
