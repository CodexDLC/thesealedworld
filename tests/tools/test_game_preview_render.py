from pathlib import Path

from tools.game_preview.fixtures import build_fixture
from tools.game_preview.render import main, render_preview
from tools.game_preview.server import _catalog_bootstrap_payload


def test_game_preview_renders_combat_fixture_with_source_css() -> None:
    fixture = build_fixture("combat/active_10_abilities")

    html = render_preview(template_name=fixture.template, fixture=fixture)

    assert "/static/css/game.css" in html
    assert "Combat Preview: 10 abilities" in html
    assert "combat-token-strip" in html
    assert "combat-ability-strip" in html
    assert html.index("combat-token-strip") < html.index("combat-ability-strip")
    assert html.count("combat-ability-option") >= 10


def test_game_preview_can_render_empty_combat_feint_slots() -> None:
    fixture = build_fixture("combat/active_10_abilities", {"feints": "0"})

    html = render_preview(template_name=fixture.template, fixture=fixture)

    assert html.count("combat-feint-row--empty") == 3
    assert "Нет приема" in html


def test_game_preview_cli_writes_output(tmp_path: Path) -> None:
    out_path = tmp_path / "combat.html"

    exit_code = main(["--fixture", "combat/active_8_abilities", "--out", str(out_path)])

    html = out_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "fixture: Combat Preview: 8 abilities" in html
    assert "template: game/session_content_inner.html" in html
    assert "combat-screen-shell" in html


def test_game_preview_catalog_bootstrap_is_valid_empty_catalog() -> None:
    payload = _catalog_bootstrap_payload()

    assert payload == {
        "version": "preview",
        "manifest": {"version": "preview", "catalogs": {}},
        "catalogs": {},
    }
