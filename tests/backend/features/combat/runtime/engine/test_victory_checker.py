from __future__ import annotations

from typing import Any

from src.backend.features.combat.dto.session import BattleMeta


class _NoBattleEndedInfoLogger:
    def bind(self, **fields: Any) -> _NoBattleEndedInfoLogger:
        raise AssertionError("VictoryChecker must not log battle-ended summaries at INFO level")

    def trace(self, message: str) -> None:
        return None


def _meta(*, dead_actors: list[str]) -> BattleMeta:
    return BattleMeta(
        active=1,
        step_counter=1,
        active_actors_count=2,
        teams={"blue": ["blue-1"], "red": ["red-1"]},
        dead_actors=dead_actors,
        battle_type="test",
        location_id="arena",
    )


def test_victory_checker_returns_winner_without_info_summary_log(monkeypatch) -> None:
    import src.backend.features.combat.runtime.engine.victory_checker as victory_checker

    monkeypatch.setattr(victory_checker, "log", _NoBattleEndedInfoLogger())

    assert victory_checker.VictoryChecker.check_battle_end(_meta(dead_actors=["blue-1"])) == "red"


def test_victory_checker_returns_draw_without_info_summary_log(monkeypatch) -> None:
    import src.backend.features.combat.runtime.engine.victory_checker as victory_checker

    monkeypatch.setattr(victory_checker, "log", _NoBattleEndedInfoLogger())

    assert victory_checker.VictoryChecker.check_battle_end(_meta(dead_actors=["blue-1", "red-1"])) == "draw"
