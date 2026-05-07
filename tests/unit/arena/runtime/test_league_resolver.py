import pytest

from src.backend.features.arena.runtime.league_resolver import LeagueResolver


def test_resolves_default_league_boundaries() -> None:
    resolver = LeagueResolver()

    assert resolver.resolve(0).code == "rookie"
    assert resolver.resolve(1199).code == "rookie"
    assert resolver.resolve(1200).code == "fighter"
    assert resolver.resolve(2100).code == "legend"
    assert resolver.resolve(9999).code == "legend"


def test_floor_for_tier_returns_min_rating() -> None:
    resolver = LeagueResolver()

    assert resolver.floor_for_tier(1) == 0
    assert resolver.floor_for_tier(4) == 1600


def test_floor_for_unknown_tier_fails() -> None:
    resolver = LeagueResolver()

    with pytest.raises(ValueError, match="unknown arena league tier"):
        resolver.floor_for_tier(99)
