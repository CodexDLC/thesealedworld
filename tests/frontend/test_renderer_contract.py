from types import SimpleNamespace

import pytest

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
