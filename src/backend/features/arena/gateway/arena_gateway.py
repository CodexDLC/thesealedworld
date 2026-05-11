from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from src.backend.features.arena.gateway.payload import payload_bool, payload_int, payload_str
from src.backend.features.arena.gateway.responses import (
    arena_error,
    arena_response,
    combat_transition,
    exploration_transition,
)
from src.shared.schemas.arena import ArenaActionDTO, ArenaActionEnum
from src.shared.schemas.response import CoreResponseDTO

if TYPE_CHECKING:
    from src.backend.features.arena.services import ArenaDuelService, ArenaGroupService, ArenaService
    from src.backend.features_site.auth.models import User

ActionHandler = Callable[[int, ArenaActionDTO], Awaitable[CoreResponseDTO[Any]]]


class ArenaGateway:
    def __init__(
        self,
        *,
        arena: ArenaService,
        duel: ArenaDuelService,
        group: ArenaGroupService,
    ) -> None:
        self.arena = arena
        self.duel = duel
        self.group = group
        self._arena_actions: dict[str, ActionHandler] = {
            ArenaActionEnum.MENU_MAIN.value: self._main_menu,
            ArenaActionEnum.LEAVE.value: self._leave,
        }
        self._duel_actions: dict[str, ActionHandler] = {
            ArenaActionEnum.MENU_MODE.value: self._duel_menu,
            ArenaActionEnum.JOIN_QUEUE.value: self._join_duel_queue,
            ArenaActionEnum.START_SHADOW.value: self._start_shadow,
            ArenaActionEnum.CHECK_MATCH.value: self._check_match,
            ArenaActionEnum.ACCEPT_SHADOW.value: self._accept_shadow,
            ArenaActionEnum.CONTINUE_SEARCH.value: self._continue_search,
            ArenaActionEnum.CHECK_COMBAT_READY.value: self._check_combat_ready,
            ArenaActionEnum.CANCEL_QUEUE.value: self._cancel_duel_queue,
        }
        self._group_actions: dict[str, ActionHandler] = {
            "group_ranked": self._group_action,
            "group_custom_request": self._group_action,
            "group_chaos": self._group_action,
            "group_watch": self._group_action,
            "group_intervene": self._group_action,
            "group_chaos_details": self._group_action,
            "group_chaos_join": self._group_action,
            "group_request_join": self._group_action,
            "group_pick_team": self._group_action,
        }

    async def get_arena_view(self, user: User, char_id: int) -> CoreResponseDTO[Any]:
        _ = user
        return await self._arena_response(char_id, await self.arena.view(char_id))

    async def handle_arena_action(self, user: User, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        _ = user
        return await self._dispatch(self._arena_actions, char_id, body, action_scope="arena")

    async def get_duel_view(self, user: User, char_id: int) -> CoreResponseDTO[Any]:
        _ = user
        return await self._arena_response(char_id, await self.duel.view(char_id))

    async def handle_duel_action(self, user: User, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        _ = user
        return await self._dispatch(self._duel_actions, char_id, body, action_scope="duel")

    async def get_group_view(self, user: User, char_id: int) -> CoreResponseDTO[Any]:
        _ = user
        return await self._arena_response(char_id, await self.group.view(char_id))

    async def handle_group_action(self, user: User, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        _ = user
        return await self._dispatch(self._group_actions, char_id, body, action_scope="group")

    async def _dispatch(
        self,
        actions: dict[str, ActionHandler],
        char_id: int,
        body: ArenaActionDTO,
        *,
        action_scope: str,
    ) -> CoreResponseDTO[Any]:
        action = str(body.action)
        handler = actions.get(action)
        if handler is None:
            return arena_error(f"Unknown {action_scope} action: {action}")
        try:
            return await handler(char_id, body)
        except ValueError as exc:
            return arena_error(str(exc))

    async def _main_menu(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        _ = body
        return await self._arena_response(char_id, await self.arena.show_main_menu(char_id))

    async def _leave(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        _ = body
        await self.arena.leave(char_id)
        return exploration_transition(char_id, reason="arena_leave")

    async def _duel_menu(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        _ = body
        return await self._arena_response(char_id, await self.duel.show_menu(char_id))

    async def _join_duel_queue(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        wait_limit_sec = payload_int(body, "wait_limit_sec", default=60)
        return await self._arena_response(char_id, await self.duel.join_queue(char_id, wait_limit_sec=wait_limit_sec))

    async def _start_shadow(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        _ = body
        return await self._arena_response(char_id, await self.duel.start_shadow(char_id))

    async def _check_match(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        _ = body
        return await self._arena_response(char_id, await self.duel.check_match(char_id))

    async def _accept_shadow(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        payload = await self.duel.accept_shadow(char_id, arena_session_id=payload_str(body, "arena_session_id"))
        if payload.combat_id:
            return combat_transition(char_id, payload, reason="arena_shadow_accepted")
        return await self._arena_response(char_id, payload)

    async def _continue_search(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        return await self._arena_response(
            char_id,
            await self.duel.continue_search(char_id, arena_session_id=payload_str(body, "arena_session_id")),
        )

    async def _check_combat_ready(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        payload = await self.duel.check_combat_ready(
            char_id,
            arena_session_id=payload_str(body, "arena_session_id"),
            confirm=payload_bool(body, "confirm"),
        )
        if payload.combat_id:
            return combat_transition(char_id, payload, reason="arena_combat_ready")
        return await self._arena_response(char_id, payload)

    async def _cancel_duel_queue(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        return await self._arena_response(
            char_id,
            await self.duel.cancel_queue(char_id, arena_session_id=payload_str(body, "arena_session_id")),
        )

    async def _group_action(self, char_id: int, body: ArenaActionDTO) -> CoreResponseDTO[Any]:
        return await self._arena_response(
            char_id,
            await self.group.handle_action(str(body.action), char_id=char_id, item_id=payload_str(body, "item_id")),
        )

    async def _arena_response(self, char_id: int, payload: Any) -> CoreResponseDTO[Any]:
        enrich = getattr(self.arena, "enrich_rating", None)
        if enrich is None or "rating" in getattr(payload, "metadata", {}):
            return arena_response(payload)
        return arena_response(await enrich(char_id, payload))
