from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO
from src.backend.features.arena.resources import ArenaResources
from src.shared.schemas.arena import ArenaScreenEnum, ArenaUIPayloadDTO

if TYPE_CHECKING:
    from src.backend.features.arena.integrations import ArenaSystemIntegrator
    from src.backend.features.arena.services.arena_session_service import ArenaSessionService

MATCHMAKING_TIMEOUT = 30
COMBAT_READY_TIMEOUT = 60


class ArenaService:
    SHADOW_SESSION_TTL_SEC = 15 * 60

    def __init__(self, *, session_service: ArenaSessionService, integrator: ArenaSystemIntegrator) -> None:
        self.session = session_service
        self.integrator = integrator

    async def get_main_menu(self) -> ArenaUIPayloadDTO:
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MAIN_MENU,
            title=ArenaResources.MAIN_TITLE,
            description=ArenaResources.MAIN_DESCRIPTION,
            buttons=ArenaResources.get_main_buttons(),
        )

    async def get_mode_menu(self, mode: str) -> ArenaUIPayloadDTO:
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MODE_MENU,
            mode=mode,
            title=ArenaResources.get_mode_title(mode),
            description=ArenaResources.get_mode_description(mode),
            buttons=ArenaResources.get_mode_buttons(mode),
        )

    async def join_queue(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        gs = await self.session.join_queue(char_id, mode)
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.SEARCHING,
            mode=mode,
            title=ArenaResources.SEARCHING_TITLE,
            description=ArenaResources.SEARCHING_DESCRIPTION,
            gs=gs,
            buttons=ArenaResources.get_searching_buttons(mode),
        )

    async def check_match(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        existing = await self.session.get_match_for_char(char_id)
        if existing is not None:
            if existing.battle_type == "shadow" and existing.metadata.get("awaiting_player_choice"):
                return self._shadow_offer_payload(existing)
            return self._pending_payload(existing)

        request = await self.session.get_request_meta(char_id)
        if request is None:
            return await self.get_main_menu()

        opponent_id = await self.session.find_opponent(char_id, mode)
        if opponent_id is not None:
            match = await self._create_combat_request(char_id, opponent_id, mode, battle_type="pvp")
            return self._pending_payload(match)

        wait_time = int(time.time() - request.start_time)
        if wait_time >= MATCHMAKING_TIMEOUT:
            match = await self._create_combat_request(char_id, None, mode, battle_type="shadow")
            return self._shadow_offer_payload(match)

        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.SEARCHING,
            mode=mode,
            title=ArenaResources.SEARCHING_TITLE,
            description=ArenaResources.SEARCHING_DESCRIPTION,
            gs=request.gs,
            wait_time_sec=wait_time,
            buttons=ArenaResources.get_searching_buttons(mode),
        )

    async def check_combat_ready(
        self,
        char_id: int,
        *,
        arena_session_id: str | None = None,
    ) -> ArenaUIPayloadDTO:
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is None:
            return self._failed_payload()

        elapsed = int(time.time() - match.created_at)
        if match.status == "ready" and match.combat_id:
            await self.integrator.enter_combat(char_id, match.combat_id)
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.COMBAT_PENDING,
                title="Бой готов",
                description="Переход к боевой сессии подтвержден.",
                mode=match.mode,
                arena_session_id=match.arena_session_id,
                combat_id=match.combat_id,
                wait_time_sec=elapsed,
                buttons=[],
            )
        if match.status == "failed" or elapsed >= COMBAT_READY_TIMEOUT:
            return self._failed_payload()
        return self._pending_payload(match, wait_time_sec=elapsed, polling=True)

    async def accept_shadow(
        self,
        char_id: int,
        mode: str,
        *,
        arena_session_id: str | None = None,
    ) -> ArenaUIPayloadDTO:
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is None or match.battle_type != "shadow":
            return self._failed_payload()
        match.metadata["awaiting_player_choice"] = False
        match.updated_at = time.time()
        await self.session.update_match(match)
        return await self.check_combat_ready(char_id, arena_session_id=match.arena_session_id)

    async def continue_search(
        self,
        char_id: int,
        mode: str,
        *,
        arena_session_id: str | None = None,
    ) -> ArenaUIPayloadDTO:
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is not None:
            await self.session.delete_match(match)
        return await self.join_queue(char_id, mode)

    async def cancel_queue(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        await self.session.leave_queue(char_id, mode)
        return await self.get_mode_menu(mode)

    async def leave(self, char_id: int) -> None:
        await self.integrator.leave_arena(char_id)

    async def _create_combat_request(
        self,
        char_id: int,
        opponent_id: int | None,
        mode: str,
        *,
        battle_type: str,
    ) -> ArenaCombatRequestDTO:
        await self.session.prepare_match(char_id, opponent_id, mode)
        participants = {"team_1": [char_id], "team_2": [opponent_id] if opponent_id else []}
        match = ArenaCombatRequestDTO(
            mode=mode,
            battle_type=battle_type,  # type: ignore[arg-type]
            requested_by=char_id,
            participants=participants,
            ttl=self.SHADOW_SESSION_TTL_SEC if opponent_id is None else None,
            metadata={
                "shadow": opponent_id is None,
                "arena_mode": mode,
                "awaiting_player_choice": opponent_id is None,
            },
        )
        await self.session.create_match(match)
        await self.integrator.request_combat_session(match)
        return match

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

    @staticmethod
    def _failed_payload() -> ArenaUIPayloadDTO:
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.COMBAT_FAILED,
            title=ArenaResources.COMBAT_FAILED_TITLE,
            description=ArenaResources.COMBAT_FAILED_DESCRIPTION,
            buttons=ArenaResources.get_failed_buttons(),
        )
