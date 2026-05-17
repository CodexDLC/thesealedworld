import pytest

from src.backend.features.world.runtime.theme import WorldThemeService


@pytest.mark.unit
def test_world_theme_is_nearly_neutral_inside_d4_core():
    theme = WorldThemeService.build(52, 52, loc_id="52_52")

    assert theme.loc_id == "52_52"
    assert theme.mode == "safe"
    assert theme.intensity <= 0.08
    assert theme.css_vars["--world-accent"] == theme.accent


@pytest.mark.unit
def test_world_theme_tracks_dominant_anchor_outside_city():
    theme = WorldThemeService.build(7, 7, loc_id="7_7")

    assert theme.dominant_anchor == "north_prime"
    assert theme.mode in {"anchor", "hybrid"}
    assert theme.intensity > 0.1
    assert theme.weights["north_prime"] == max(theme.weights.values())


@pytest.mark.unit
def test_world_theme_does_not_export_interface_glass_contract():
    theme = WorldThemeService.build(7, 7, loc_id="7_7")

    assert not hasattr(theme, "glass")
    assert "--world-glass" not in theme.css_vars
