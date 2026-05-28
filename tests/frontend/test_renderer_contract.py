from pathlib import Path
from types import SimpleNamespace

import pytest

from src.frontend.core import renderer
from src.frontend.core.renderer import UIRenderer


class _Templates:
    def __init__(self) -> None:
        self.context = None

    def TemplateResponse(self, *, request, name, context, status_code):
        self.context = context
        return SimpleNamespace(request=request, name=name, context=context, status_code=status_code)


@pytest.mark.asyncio
async def test_ui_renderer_exposes_access_token_to_htmx_fragments() -> None:
    templates = _Templates()
    request = SimpleNamespace(
        headers={"HX-Request": "true"},
        cookies={"tbmmorpg_access_token": "chat-token"},
        state=SimpleNamespace(user=None),
    )

    response = await UIRenderer(request, templates).render("game/session_content.html", context={})

    assert response.context["access_token"] == "chat-token"
    assert response.context["base_template"] == "shared/minimal.html"


def test_static_version_tracks_fonts_css(monkeypatch, tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    css_dir = static_dir / "css"
    js_dir = static_dir / "js"
    state_js_dir = js_dir / "game" / "states"
    css_dir.mkdir(parents=True)
    js_dir.mkdir(parents=True)
    state_js_dir.mkdir(parents=True)

    older_assets = (
        css_dir / "site.css",
        js_dir / "site.js",
        css_dir / "game.css",
        js_dir / "game.js",
        state_js_dir / "rift.js",
        css_dir / "account.css",
        css_dir / "admin.css",
    )
    for path in older_assets:
        path.write_text("", encoding="utf-8")
        path.touch()

    fonts_css = css_dir / "fonts.css"
    fonts_css.write_text("", encoding="utf-8")
    newer_mtime = 2_000_000_000
    fonts_css.touch()
    for path in older_assets:
        path.touch()
    fonts_css.touch()
    monkeypatch.setattr(renderer.settings, "static_dir", static_dir)
    monkeypatch.setattr(renderer, "_mtime", lambda path: newer_mtime if path == fonts_css else 1)

    assert renderer._static_version() == str(newer_mtime)
