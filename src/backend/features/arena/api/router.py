from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from src.backend.features.arena.dependencies import ArenaGatewayDep, ArenaServiceDep
from src.backend.features_site.auth.dependencies import get_current_user
from src.backend.features_site.auth.models import User
from src.shared.enums import CoreDomain
from src.shared.schemas.arena import ArenaActionDTO, ArenaActionEnum, ArenaScreenEnum, ArenaUIPayloadDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader, StateTransitionDTO

router = APIRouter(prefix="/arena", tags=["Arena"])


@router.get("/v2/{char_id}/view", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_view_v2(
    char_id: int,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    return await gateway.get_arena_view(current_user, char_id)


@router.post("/v2/{char_id}/action", response_model=CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO])
async def arena_action_v2(
    char_id: int,
    body: ArenaActionDTO,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO]:
    return await gateway.handle_arena_action(current_user, char_id, body)


@router.get("/v2/{char_id}/duel/view", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_duel_view_v2(
    char_id: int,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    return await gateway.get_duel_view(current_user, char_id)


@router.post("/v2/{char_id}/duel/action", response_model=CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO])
async def arena_duel_action_v2(
    char_id: int,
    body: ArenaActionDTO,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO]:
    return await gateway.handle_duel_action(current_user, char_id, body)


@router.get("/v2/{char_id}/group/lobby", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_group_lobby_v2(
    char_id: int,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    return await gateway.get_group_view(current_user, char_id)


@router.post("/v2/{char_id}/group/action", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_group_action_v2(
    char_id: int,
    body: ArenaActionDTO,
    gateway: ArenaGatewayDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    return await gateway.handle_group_action(current_user, char_id, body)


@router.get("/view", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_view(
    service: ArenaServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
    char_id: int = Query(...),
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    _ = current_user
    payload = await service.view(char_id)
    return _arena_response(payload)


@router.get("/group/lobby", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_group_lobby(
    service: ArenaServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
    char_id: int = Query(...),
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    _ = current_user
    return _arena_response(await service.show_group_lobby(char_id))


@router.post("/{char_id}/action", response_model=CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO])
async def arena_action(
    char_id: int,
    body: ArenaActionDTO,
    service: ArenaServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO]:
    _ = current_user
    await service.enter_arena(char_id)
    action = str(body.action)
    mode = str(body.mode) if body.mode else None
    value = body.value or {}

    if action == ArenaActionEnum.MENU_MAIN.value:
        return _arena_response(await service.show_main_menu(char_id))
    if action == ArenaActionEnum.MENU_MODE.value:
        return _arena_response(await service.show_mode_menu(char_id, _require_mode(mode)))
    if action == ArenaActionEnum.JOIN_QUEUE.value:
        return _arena_response(
            await service.join_queue(
                char_id,
                _require_mode(mode),
                wait_limit_sec=int(value.get("wait_limit_sec") or 60),
            )
        )
    if action == ArenaActionEnum.START_SHADOW.value:
        return _arena_response(await service.start_shadow(char_id, _require_mode(mode)))
    if action == ArenaActionEnum.CHECK_MATCH.value:
        return _arena_response(await service.check_match(char_id, _require_mode(mode)))
    if action == ArenaActionEnum.ACCEPT_SHADOW.value:
        payload = await service.accept_shadow(
            char_id,
            _require_mode(mode),
            arena_session_id=value.get("arena_session_id"),
        )
        if payload.combat_id:
            transition = StateTransitionDTO(
                char_id=char_id,
                target_state=CoreDomain.COMBAT,
                reason="arena_shadow_accepted",
                combat_id=payload.combat_id,
                arena_id=payload.arena_session_id,
                metadata=payload.model_dump(mode="json"),
            )
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.COMBAT, previous_state=CoreDomain.ARENA),
                payload=transition,
                payload_type="state_transition",
            )
        return _arena_response(payload)
    if action == ArenaActionEnum.CONTINUE_SEARCH.value:
        return _arena_response(
            await service.continue_search(
                char_id,
                _require_mode(mode),
                arena_session_id=value.get("arena_session_id"),
            )
        )
    if action == ArenaActionEnum.CHECK_COMBAT_READY.value:
        payload = await service.check_combat_ready(
            char_id,
            arena_session_id=value.get("arena_session_id"),
            confirm=bool(value.get("confirm")),
        )
        if payload.combat_id:
            transition = StateTransitionDTO(
                char_id=char_id,
                target_state=CoreDomain.COMBAT,
                reason="arena_combat_ready",
                combat_id=payload.combat_id,
                arena_id=payload.arena_session_id,
                metadata=payload.model_dump(mode="json"),
            )
            return CoreResponseDTO(
                header=GameStateHeader(current_state=CoreDomain.COMBAT, previous_state=CoreDomain.ARENA),
                payload=transition,
                payload_type="state_transition",
            )
        return _arena_response(payload)
    if action == ArenaActionEnum.CANCEL_QUEUE.value:
        return _arena_response(
            await service.cancel_queue(
                char_id,
                _require_mode(mode),
                arena_session_id=value.get("arena_session_id"),
            )
        )
    if action == ArenaActionEnum.LEAVE.value:
        await service.leave(char_id)
        transition = StateTransitionDTO(char_id=char_id, target_state=CoreDomain.EXPLORATION, reason="arena_leave")
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.EXPLORATION, previous_state=CoreDomain.ARENA),
            payload=transition,
            payload_type="state_transition",
        )

    payload = ArenaUIPayloadDTO(
        screen=ArenaScreenEnum.MATCH_FOUND,  # Use enum value
        title="Ошибка арены",
        description=f"Неизвестное действие: {action}",
        buttons=[],
    )
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.ARENA, error=f"Unknown action: {action}"),
        payload=payload,
        payload_type="arena_error",
    )


@router.post("/{char_id}/group/action", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_group_action(
    char_id: int,
    body: ArenaActionDTO,
    service: ArenaServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    _ = current_user
    await service.enter_arena(char_id)
    value = body.value if isinstance(body.value, dict) else {}
    return _arena_response(await service.group_action(str(body.action), char_id=char_id, item_id=value.get("item_id")))


def _arena_response(payload: ArenaUIPayloadDTO) -> CoreResponseDTO[Any]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.ARENA),
        payload=payload,
        payload_type="arena_screen",
    )


def _require_mode(mode: str | None) -> str:
    if not mode:
        return "one_vs_one"
    return mode
