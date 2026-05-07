from src.backend.features.arena.runtime.rating import RatingCalculator, RatingTeamInput
from src.backend.features.arena.runtime.rules.elo import K_BASE, K_PLACEMENT


def test_expected_score_is_symmetric() -> None:
    calculator = RatingCalculator()

    expected_a = calculator.expected_score(1000, 1200)
    expected_b = calculator.expected_score(1200, 1000)

    assert round(expected_a + expected_b, 10) == 1.0


def test_gs_modifier_rewards_low_gear_upset_and_penalizes_high_gear_loss() -> None:
    calculator = RatingCalculator()

    low_gear_win = calculator.gs_modifier(900, 1100, 1.0)
    high_gear_loss = calculator.gs_modifier(1100, 900, 0.0)

    assert low_gear_win == 1.2
    assert high_gear_loss == 1.2


def test_gs_modifier_clamps_to_configured_band() -> None:
    calculator = RatingCalculator()

    assert calculator.gs_modifier(100, 1000, 1.0) == 1.2
    assert calculator.gs_modifier(1000, 100, 1.0) == 0.8


def test_placement_uses_larger_k_than_base() -> None:
    calculator = RatingCalculator()

    base = calculator.compute_delta(1000, 1000, 1000, 1000, 1.0)
    placement = calculator.compute_delta(1000, 1000, 1000, 1000, 1.0, in_placement=True)

    assert base.k == K_BASE
    assert placement.k == K_PLACEMENT
    assert placement.delta > base.delta


def test_draw_equal_ratings_sums_to_zero() -> None:
    calculator = RatingCalculator()

    delta_a, delta_b = calculator.compute_match_deltas(
        RatingTeamInput(rating=1000, gear_score=1000),
        RatingTeamInput(rating=1000, gear_score=1200),
        "draw",
    )

    assert delta_a.delta + delta_b.delta == 0


def test_win_loss_deltas_are_opposite_when_gear_is_equal() -> None:
    calculator = RatingCalculator()

    delta_a, delta_b = calculator.compute_match_deltas(
        RatingTeamInput(rating=1000, gear_score=1000),
        RatingTeamInput(rating=1000, gear_score=1000),
        "team_a",
    )

    assert delta_a.delta == -delta_b.delta
    assert delta_a.delta > 0
