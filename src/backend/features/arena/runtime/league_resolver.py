from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.arena.runtime.rules.leagues import DEFAULT_LEAGUES, LeagueRule

if TYPE_CHECKING:
    from collections.abc import Sequence


class LeagueResolver:
    def __init__(self, leagues: Sequence[LeagueRule] = DEFAULT_LEAGUES) -> None:
        self.leagues = tuple(sorted(leagues, key=lambda league: league.tier))

    def resolve(self, rating: int) -> LeagueRule:
        for league in self.leagues:
            if rating >= league.min_rating and (league.max_rating is None or rating <= league.max_rating):
                return league
        if not self.leagues:
            raise ValueError("at least one league rule is required")
        return self.leagues[-1]

    def floor_for_tier(self, tier: int) -> int:
        for league in self.leagues:
            if league.tier == tier:
                return league.min_rating
        raise ValueError(f"unknown arena league tier: {tier}")
