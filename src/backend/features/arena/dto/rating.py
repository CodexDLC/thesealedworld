from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime as dt


@dataclass(frozen=True, slots=True)
class RatingSnapshotDTO:
    entity_type: str
    entity_id: int
    mode_size: int
    season_id: int
    rating: int
    peak_rating: int
    wins: int
    losses: int
    draws: int
    league_tier: int
    matches_played: int
    placement_left: int


@dataclass(frozen=True, slots=True)
class LeaderboardEntryDTO(RatingSnapshotDTO):
    rank: int


@dataclass(frozen=True, slots=True)
class MatchTeamDTO:
    entity_type: str
    entity_id: int
    member_ids: list[int]
    gs_locked: int
    gs_per_member: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MatchResultDTO:
    combat_id: str | None
    arena_session_id: str
    mode: str
    mode_size: int
    season_id: int
    team_a: MatchTeamDTO
    team_b: MatchTeamDTO
    winner: str
    created_at: dt.datetime
    completed_at: dt.datetime
