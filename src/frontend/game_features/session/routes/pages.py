from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.game_features.session.cookies import active_character_id_from_cookie
from src.frontend.game_features.session.dependencies import get_session_context_builder
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.site_features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.site_features.auth.services.auth_service import FrontendAuthService
from src.shared.enums import CoreDomain

router = APIRouter(tags=["Game Session"])


@router.get("/game/session", name="game_session")
async def game_session(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
):
    user = await auth_service.require_current_user(request)
    char_id = active_character_id_from_cookie(request)
    context = await context_builder.build_current(request, char_id=char_id)
    context["user"] = user
    return await ui.render("game/session.html", context=context)


@router.get("/game/session/state/{state}", name="game_session_state")
async def game_session_state(
    state: CoreDomain,
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int | None, Query()] = None,
    quest_key: Annotated[str | None, Query()] = None,
):
    user = await auth_service.require_current_user(request)
    active_char_id = char_id if char_id is not None else active_character_id_from_cookie(request)
    context = await context_builder.build(request, state=state, char_id=active_char_id, quest_key=quest_key)
    context["user"] = user
    return await ui.render("game/session.html", context=context)
