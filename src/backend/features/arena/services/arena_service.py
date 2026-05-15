from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.backend.features.arena.resources import ArenaResources
from src.shared.schemas.arena import ArenaModeEnum, ArenaScreenEnum, ArenaUIPayloadDTO

if TYPE_CHECKING:
    from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaRuntimeSessionDTO
    from src.backend.features.arena.integrations import ArenaSessionIntegration, ArenaSystemIntegrator
    from src.backend.features.arena.services.rating_view_service import ArenaRatingViewService

COMBAT_READY_TIMEOUT = 60


class ArenaService:
    SHADOW_SESSION_TTL_SEC = 15 * 60

    def __init__(
        self,
        *,
        session_service: ArenaSessionIntegration,
        integrator: ArenaSystemIntegrator,
        rating_view: ArenaRatingViewService | None = None,
    ) -> None:
        self.session = session_service
        self.integrator = integrator
        self.rating_view = rating_view

    async def view(self, char_id: int) -> ArenaUIPayloadDTO:
        session = await self._ensure_runtime_session(char_id)
        return await self.enrich_rating(char_id, await self._payload_from_runtime_session(session))

    async def ensure_runtime_session(self, char_id: int) -> ArenaRuntimeSessionDTO:
        return await self._ensure_runtime_session(char_id)

    async def runtime_session_for_char(self, char_id: int) -> ArenaRuntimeSessionDTO | None:
        return await self._runtime_session_for_char(char_id)

    async def enrich_rating(
        self,
        char_id: int,
        payload: ArenaUIPayloadDTO,
        *,
        mode_size: int = 1,
    ) -> ArenaUIPayloadDTO:
        if self.rating_view is None:
            return payload
        metadata = await self.rating_view.player_metadata(char_id=char_id, mode_size=mode_size)
        return payload.model_copy(update={"metadata": {**payload.metadata, **metadata}})

    async def get_main_menu(self) -> ArenaUIPayloadDTO:
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MAIN_MENU,
            title=ArenaResources.MAIN_TITLE,
            description=ArenaResources.MAIN_DESCRIPTION,
            buttons=ArenaResources.get_main_buttons(),
        )

    async def show_main_menu(self, char_id: int) -> ArenaUIPayloadDTO:
        runtime_session = await self._ensure_runtime_session(char_id)
        await self.session.set_runtime_screen(runtime_session, ArenaScreenEnum.MAIN_MENU, mode=None)
        return await self.get_main_menu()

    async def leave(self, char_id: int) -> None:
        runtime_session = await self._runtime_session_for_char(char_id)
        request = await self.session.get_request_meta(char_id)
        match = await self.session.get_match_for_char(char_id)
        if match is not None:
            await self.session.delete_match(match)
        if request is not None:
            await self.session.leave_queue(char_id, request.mode)
        if runtime_session is not None:
            await self.session.delete_runtime_session(runtime_session.arena_id)
        await self.integrator.leave_arena(char_id)

    async def _ensure_runtime_session(self, char_id: int) -> ArenaRuntimeSessionDTO:
        existing_id = await self.integrator.resolve_arena_session_id(char_id)
        if existing_id:
            session = await self.session.get_runtime_session(existing_id)
            if session is not None and session.char_id == char_id:
                await self.integrator.enter_arena(char_id)
                return session
            await self.integrator.clear_arena_session(char_id)

        session = await self.session.create_runtime_session(char_id)
        await self.integrator.attach_arena_session(char_id, session.arena_id)
        await self.integrator.enter_arena(char_id)
        return session

    async def _runtime_session_for_char(self, char_id: int) -> ArenaRuntimeSessionDTO | None:
        existing_id = await self.integrator.resolve_arena_session_id(char_id)
        if not existing_id:
            return None
        session = await self.session.get_runtime_session(existing_id)
        if session is None or session.char_id != char_id:
            await self.integrator.clear_arena_session(char_id)
            return None
        return session

    async def _payload_from_runtime_session(self, session: ArenaRuntimeSessionDTO) -> ArenaUIPayloadDTO:
        match = None
        if session.active_match_id:
            match = await self.session.get_match(session.active_match_id)
        if match is None:
            match = await self.session.get_match_for_char(session.char_id)
        if match is not None:
            if match.battle_type == "shadow" and match.metadata.get("awaiting_player_choice"):
                return self._shadow_offer_payload(match)
            return self._pending_payload(match)

        if session.screen == ArenaScreenEnum.MODE_MENU and session.mode:
            return await self._mode_payload(session.mode)

        request = await self.session.get_request_meta(session.char_id)
        if request is not None:
            wait_time = int(time.time() - request.start_time)
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.SEARCHING,
                mode=request.mode,
                title=ArenaResources.SEARCHING_TITLE,
                description=ArenaResources.SEARCHING_DESCRIPTION,
                gs=request.gs,
                wait_time_sec=wait_time,
                buttons=ArenaResources.get_searching_buttons(request.mode),
                metadata={"queue_type": "ranked", "wait_limit_sec": request.wait_limit_sec},
            )

        if session.screen in {ArenaScreenEnum.COMBAT_FAILED, ArenaScreenEnum.COMBAT_PENDING}:
            await self.session.set_runtime_screen(session, ArenaScreenEnum.MAIN_MENU, mode=None)
        return await self.get_main_menu()

    async def _mode_payload(self, mode: str) -> ArenaUIPayloadDTO:
        metadata = {}
        if mode == ArenaModeEnum.GROUP.value:
            metadata["group_lobby"] = ArenaResources.get_group_lobby_mock()
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MODE_MENU,
            mode=mode,
            title=ArenaResources.get_mode_title(mode),
            description=ArenaResources.get_mode_description(mode),
            buttons=ArenaResources.get_mode_buttons(mode),
            metadata=metadata,
        )

    def _pending_payload(
        self,
        match: ArenaCombatRequestDTO,
        *,
        wait_time_sec: int = 0,
        polling: bool = False,
    ) -> ArenaUIPayloadDTO:
        is_shadow = match.battle_type == "shadow"
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.COMBAT_PENDING,
            mode=match.mode,
            title=ArenaResources.SHADOW_PENDING_TITLE if is_shadow else ArenaResources.PVP_PENDING_TITLE,
            description=(
                ArenaResources.SHADOW_PENDING_DESCRIPTION if is_shadow else ArenaResources.PVP_PENDING_DESCRIPTION
            ),
            arena_session_id=match.arena_session_id,
            wait_time_sec=wait_time_sec,
            poll_after_ms=1000,
            timeout_sec=COMBAT_READY_TIMEOUT,
            buttons=ArenaResources.get_pending_buttons(match.mode, match.arena_session_id),
            metadata={"battle_type": match.battle_type, "polling": polling, **match.metadata},
        )

    @staticmethod
    def _shadow_offer_payload(match: ArenaCombatRequestDTO) -> ArenaUIPayloadDTO:
        wait_time = int(time.time() - match.created_at)
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.SHADOW_OFFER,
            mode=match.mode,
            title=ArenaResources.SHADOW_OFFER_TITLE,
            description=ArenaResources.SHADOW_OFFER_DESCRIPTION,
            arena_session_id=match.arena_session_id,
            wait_time_sec=wait_time,
            timeout_sec=900,
            buttons=ArenaResources.get_shadow_offer_buttons(match.mode, match.arena_session_id),
            metadata={"battle_type": match.battle_type, "polling": False, **match.metadata},
        )
