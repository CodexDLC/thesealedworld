from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.backend.features.arena.dependencies import ArenaServiceDep
from src.backend.features_site.auth.dependencies import get_current_user
from src.backend.features_site.auth.models import User
from src.shared.enums import CoreDomain
from src.shared.schemas.arena import ArenaActionDTO, ArenaActionEnum, ArenaUIPayloadDTO
from src.shared.schemas.response import CoreResponseDTO, GameStateHeader, StateTransitionDTO

router = APIRouter(prefix="/arena", tags=["Arena"])


@router.get("/view", response_model=CoreResponseDTO[ArenaUIPayloadDTO])
async def arena_view(
    service: ArenaServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
    char_id: int = Query(...),
) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    _ = current_user, char_id
    payload = await service.get_main_menu()
    return _arena_response(payload)


@router.post("/{char_id}/action", response_model=CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO])
async def arena_action(
    char_id: int,
    body: ArenaActionDTO,
    service: ArenaServiceDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoreResponseDTO[ArenaUIPayloadDTO | StateTransitionDTO]:
    _ = current_user
    action = str(body.action)
    mode = str(body.mode) if body.mode else None
    value = body.value or {}

    if action == ArenaActionEnum.MENU_MAIN.value:
        return _arena_response(await service.get_main_menu())
    if action == ArenaActionEnum.MENU_MODE.value:
        return _arena_response(await service.get_mode_menu(_require_mode(mode)))
    if action == ArenaActionEnum.JOIN_QUEUE.value:
        return _arena_response(await service.join_queue(char_id, _require_mode(mode)))
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
        payload = await service.check_combat_ready(char_id, arena_session_id=value.get("arena_session_id"))
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
        return _arena_response(await service.cancel_queue(char_id, _require_mode(mode)))
    if action == ArenaActionEnum.LEAVE.value:
        await service.leave(char_id)
        transition = StateTransitionDTO(char_id=char_id, target_state=CoreDomain.EXPLORATION, reason="arena_leave")
        return CoreResponseDTO(
            header=GameStateHeader(current_state=CoreDomain.EXPLORATION, previous_state=CoreDomain.ARENA),
            payload=transition,
            payload_type="state_transition",
        )

    payload = ArenaUIPayloadDTO(
        screen="main_menu",
        title="Ошибка арены",
        description=f"Неизвестное действие: {action}",
        buttons=[],
    )
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.ARENA, error=f"Unknown action: {action}"),
        payload=payload,
        payload_type="arena_error",
    )


def _arena_response(payload: ArenaUIPayloadDTO) -> CoreResponseDTO[ArenaUIPayloadDTO]:
    return CoreResponseDTO(
        header=GameStateHeader(current_state=CoreDomain.ARENA),
        payload=payload,
        payload_type="arena_screen",
    )


def _require_mode(mode: str | None) -> str:
    if not mode:
        return "one_vs_one"
    return mode
