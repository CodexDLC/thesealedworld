from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LeagueRule:
    tier: int
    code: str
    name: str
    min_rating: int
    max_rating: int | None = None


DEFAULT_LEAGUES: tuple[LeagueRule, ...] = (
    LeagueRule(1, "rookie", "Rookie", 0, 1199),
    LeagueRule(2, "fighter", "Fighter", 1200, 1399),
    LeagueRule(3, "challenger", "Challenger", 1400, 1599),
    LeagueRule(4, "veteran", "Veteran", 1600, 1799),
    LeagueRule(5, "elite", "Elite", 1800, 2099),
    LeagueRule(6, "legend", "Legend", 2100, None),
)
