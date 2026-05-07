from __future__ import annotations

from dataclasses import dataclass

from src.backend.features.arena.runtime.rules.elo import DRAW_SCORE, GS_DELTA_NORM, GS_MOD_MAX, K_BASE, K_PLACEMENT


@dataclass(frozen=True, slots=True)
class RatingTeamInput:
    rating: int
    gear_score: int
    in_placement: bool = False


@dataclass(frozen=True, slots=True)
class RatingDelta:
    score: float
    expected_score: float
    delta: int
    k: float
    gs_modifier: float


class RatingCalculator:
    @staticmethod
    def expected_score(rating_self: int, rating_opp: int) -> float:
        return 1 / (1 + 10 ** ((rating_opp - rating_self) / 400))

    @staticmethod
    def gs_modifier(gs_self: int, gs_opp: int, score: float) -> float:
        delta = _clamp((gs_self - gs_opp) / GS_DELTA_NORM, -1.0, 1.0)
        if score > DRAW_SCORE:
            return 1.0 + GS_MOD_MAX * (-delta)
        if score < DRAW_SCORE:
            return 1.0 + GS_MOD_MAX * delta
        return 1.0

    def compute_delta(
        self,
        rating_self: int,
        rating_opp: int,
        gs_self: int,
        gs_opp: int,
        score: float,
        *,
        in_placement: bool = False,
    ) -> RatingDelta:
        expected = self.expected_score(rating_self, rating_opp)
        modifier = self.gs_modifier(gs_self, gs_opp, score)
        k = (K_PLACEMENT if in_placement else K_BASE) * modifier
        return RatingDelta(
            score=score, expected_score=expected, delta=round(k * (score - expected)), k=k, gs_modifier=modifier
        )

    def compute_match_deltas(
        self,
        team_a: RatingTeamInput,
        team_b: RatingTeamInput,
        winner: str,
    ) -> tuple[RatingDelta, RatingDelta]:
        score_a, score_b = _scores_for_winner(winner)
        return (
            self.compute_delta(
                team_a.rating,
                team_b.rating,
                team_a.gear_score,
                team_b.gear_score,
                score_a,
                in_placement=team_a.in_placement,
            ),
            self.compute_delta(
                team_b.rating,
                team_a.rating,
                team_b.gear_score,
                team_a.gear_score,
                score_b,
                in_placement=team_b.in_placement,
            ),
        )


def _scores_for_winner(winner: str) -> tuple[float, float]:
    if winner == "team_a":
        return 1.0, 0.0
    if winner == "team_b":
        return 0.0, 1.0
    if winner == "draw":
        return DRAW_SCORE, DRAW_SCORE
    raise ValueError(f"unsupported arena winner: {winner}")


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
