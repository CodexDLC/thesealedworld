from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Form, Request
from loguru import logger

from src.frontend.core.renderer import UIRenderer, get_ui_renderer
from src.frontend.features.auth.dependencies.providers import get_frontend_auth_service
from src.frontend.features.auth.services.auth_service import FrontendAuthService
from src.frontend.game_features.session.dependencies import get_backend_combat_api, get_session_context_builder
from src.frontend.game_features.session.services.session_context_builder import SessionContextBuilder
from src.frontend.game_features.session.token_state import require_game_access_token
from src.frontend.integrations.backend_api.combat import BackendCombatApi
from src.shared.schemas.combat import (
    CombatDashboardDTO,
    CombatErrorDTO,
    CombatEventDTO,
    CombatPinFeintRequestDTO,
    CombatRegisterMoveRequestDTO,
    CombatResultDTO,
)

router = APIRouter(tags=["Combat"])
LOG_PAGE_SIZE_OPTIONS = (4, 8, 12)


@router.get("/game/combat/logs", name="game_combat_logs")
async def game_combat_logs(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    combat_api: Annotated[BackendCombatApi, Depends(get_backend_combat_api)],
    char_id: int,
    page: int = 1,
    page_size: int = 8,
):
    await auth_service.require_current_user(request)
    token = require_game_access_token(request)
    page_size = _allowed_page_size(page_size)
    logs = await combat_api.logs(token, char_id=char_id, page=max(1, page), page_size=page_size)
    total_turns = getattr(logs, "total_turns", 0) or logs.total
    total_pages = max(1, (total_turns + logs.page_size - 1) // logs.page_size)
    active_page = min(max(1, logs.page), total_pages)
    return await ui.render(
        "game/domains/combat/viewport/log_panel.html",
        context={
            "char_id": char_id,
            "combat_log_entries": logs.entries,
            "combat_log_turns": logs.turns,
            "combat_log_page": active_page,
            "combat_log_page_size": logs.page_size,
            "combat_log_page_size_options": LOG_PAGE_SIZE_OPTIONS,
            "combat_log_total": total_turns,
            "combat_log_total_pages": total_pages,
            "combat_log_pages": _page_window(active_page, total_pages),
        },
    )


@router.post("/game/combat/move", name="game_combat_move")
async def game_combat_move(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    combat_api: Annotated[BackendCombatApi, Depends(get_backend_combat_api)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int, Form()],
    action: Annotated[str, Form()],
    target_id: Annotated[str | None, Form()] = None,
    feint_id: Annotated[str | None, Form()] = None,
    ability_id: Annotated[str | None, Form()] = None,
):
    await auth_service.require_current_user(request)
    token = require_game_access_token(request)
    try:
        combat_payload = await combat_api.register_move(
            token,
            char_id=char_id,
            body=CombatRegisterMoveRequestDTO(
                action=action,
                target_id=_blank_to_none(target_id),
                feint_id=_blank_to_none(feint_id),
                ability_id=_blank_to_none(ability_id),
            ),
        )
    except httpx.HTTPStatusError as exc:
        error = _backend_combat_error(exc)
        logger.warning(
            "Combat move rejected: char_id={} action={} code={} detail={}", char_id, action, error.code, error.message
        )
        combat_payload = await combat_api.snapshot(token, char_id=char_id)
        dashboard = combat_payload
        _append_rejected_move_event(dashboard, error)
    if isinstance(combat_payload, CombatResultDTO):
        context = context_builder.build_combat_result_context(combat_payload, char_id=char_id)
    else:
        dashboard = combat_payload
        context = context_builder.build_combat_dashboard_context(dashboard, char_id=char_id)
    return await ui.render("game/session_content_inner.html", context=context)


@router.post("/game/combat/result/continue", name="game_combat_result_continue")
async def game_combat_result_continue(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    combat_api: Annotated[BackendCombatApi, Depends(get_backend_combat_api)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int, Form()],
):
    await auth_service.require_current_user(request)
    token = require_game_access_token(request)
    response = await combat_api.continue_result(token, char_id=char_id)
    context = await context_builder.build_from_response(request, response, char_id=char_id)
    return await ui.render("game/session_content_inner.html", context=context)


@router.post("/game/combat/feint-pin", name="game_combat_feint_pin")
async def game_combat_feint_pin(
    request: Request,
    ui: Annotated[UIRenderer, Depends(get_ui_renderer)],
    auth_service: Annotated[FrontendAuthService, Depends(get_frontend_auth_service)],
    combat_api: Annotated[BackendCombatApi, Depends(get_backend_combat_api)],
    context_builder: Annotated[SessionContextBuilder, Depends(get_session_context_builder)],
    char_id: Annotated[int, Form()],
    feint_id: Annotated[str | None, Form()] = None,
):
    await auth_service.require_current_user(request)
    token = require_game_access_token(request)
    try:
        dashboard = await combat_api.pin_feint(
            token,
            char_id=char_id,
            body=CombatPinFeintRequestDTO(feint_id=_blank_to_none(feint_id)),
        )
    except httpx.HTTPStatusError as exc:
        error = _backend_combat_error(exc)
        logger.warning(
            "Combat feint pin rejected: char_id={} feint_id={} code={} detail={}",
            char_id,
            feint_id,
            error.code,
            error.message,
        )
        dashboard = await combat_api.snapshot(token, char_id=char_id)
        _append_rejected_move_event(dashboard, error)
    context = context_builder.build_combat_dashboard_context(dashboard, char_id=char_id)
    return await ui.render("game/session_content_inner.html", context=context)


def _blank_to_none(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    return value


def _allowed_page_size(page_size: int) -> int:
    return max(1, min(page_size, 50))


def _page_window(active_page: int, total_pages: int) -> list[int]:
    first = max(1, active_page - 1)
    last = min(total_pages, first + 3)
    first = max(1, last - 3)
    return list(range(first, last + 1))


def _backend_combat_error(exc: httpx.HTTPStatusError) -> CombatErrorDTO:
    fallback = f"Backend rejected combat move with status {exc.response.status_code}"
    try:
        data = exc.response.json()
    except ValueError:
        return CombatErrorDTO(code="combat_http_error", message=exc.response.text or fallback)
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            return CombatErrorDTO.model_validate(error)
        detail = data.get("detail")
        if detail:
            return CombatErrorDTO(code="combat_http_error", message=str(detail))
    return CombatErrorDTO(code="combat_http_error", message=fallback)


def _append_rejected_move_event(dashboard: CombatDashboardDTO, error: CombatErrorDTO) -> None:
    dashboard.events_delta.events.append(
        CombatEventDTO(
            type="error",
            text=error.message,
            tags=["combat_move_rejected"],
            data={"code": error.code, "detail": error.message, "context": error.context},
        )
    )
