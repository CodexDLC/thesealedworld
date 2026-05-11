from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaRuntimeSessionDTO
from src.backend.features.arena.resources import ArenaResources
from src.shared.schemas.arena import ArenaScreenEnum, ArenaUIPayloadDTO

if TYPE_CHECKING:
    from src.backend.features.arena.integrations import ArenaSessionIntegration, ArenaSystemIntegrator

COMBAT_READY_TIMEOUT = 60
ARENA_SNAPSHOT_GRACE_SEC = 10 * 60
ARENA_COMMITMENT_GRACE_SEC = ARENA_SNAPSHOT_GRACE_SEC


class ArenaService:
    SHADOW_SESSION_TTL_SEC = 15 * 60

    def __init__(self, *, session_service: ArenaSessionIntegration, integrator: ArenaSystemIntegrator) -> None:
        self.session = session_service
        self.integrator = integrator

    async def enter_arena(self, char_id: int) -> None:
        await self._ensure_runtime_session(char_id)

    async def view(self, char_id: int) -> ArenaUIPayloadDTO:
        session = await self._ensure_runtime_session(char_id)
        return await self._payload_from_runtime_session(session)

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

    async def get_mode_menu(self, mode: str) -> ArenaUIPayloadDTO:
        metadata = {}
        if mode == "group":
            metadata["group_lobby"] = ArenaResources.get_group_lobby_mock()
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MODE_MENU,
            mode=mode,
            title=ArenaResources.get_mode_title(mode),
            description=ArenaResources.get_mode_description(mode),
            buttons=ArenaResources.get_mode_buttons(mode),
            metadata=metadata,
        )

    async def show_mode_menu(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        runtime_session = await self._ensure_runtime_session(char_id)
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.MODE_MENU,
            mode=mode,
            active_match_id="",
            combat_id="",
            metadata={"group_lobby_open": mode == "group"},
        )
        return await self.get_mode_menu(mode)

    async def get_group_lobby(self) -> ArenaUIPayloadDTO:
        return await self.get_mode_menu("group")

    async def show_group_lobby(self, char_id: int) -> ArenaUIPayloadDTO:
        return await self.show_mode_menu(char_id, "group")

    async def group_action(
        self, action: str, *, char_id: int | None = None, item_id: str | None = None
    ) -> ArenaUIPayloadDTO:
        if char_id is not None:
            runtime_session = await self._ensure_runtime_session(char_id)
            await self.session.set_runtime_screen(
                runtime_session,
                ArenaScreenEnum.MODE_MENU,
                mode="group",
                metadata={"group_action": action, "group_item_id": item_id or ""},
            )
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MODE_MENU,
            mode="group",
            title=ArenaResources.get_mode_title("group"),
            description=ArenaResources.get_mode_description("group"),
            buttons=ArenaResources.get_mode_buttons("group"),
            metadata={
                "group_lobby": ArenaResources.get_group_lobby_mock(),
                "group_action": ArenaResources.get_group_action_mock(action, item_id),
            },
        )

    async def join_queue(self, char_id: int, mode: str, *, wait_limit_sec: int = 60) -> ArenaUIPayloadDTO:
        runtime_session = await self._ensure_runtime_session(char_id)
        wait_limit_sec = self._normalize_wait_limit(wait_limit_sec)
        request_id = f"arena:{uuid.uuid4().hex[:12]}"
        commitment_ttl = wait_limit_sec + ARENA_COMMITMENT_GRACE_SEC
        commitment_id = await self.integrator.create_combat_commitment(
            request_id=request_id,
            char_id=char_id,
            ttl=commitment_ttl,
        )
        if not commitment_id:
            await self.session.set_runtime_screen(
                runtime_session,
                ArenaScreenEnum.MODE_MENU,
                mode=mode,
                metadata={"commitment_status": "failed", "commitment_ttl": commitment_ttl},
            )
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.MODE_MENU,
                mode=mode,
                title="Боевая сигнатура недоступна",
                description="Арена не смогла зафиксировать боевую заявку. Повторите поиск позже.",
                buttons=ArenaResources.get_mode_buttons(mode),
                metadata={"commitment_status": "failed", "commitment_ttl": commitment_ttl},
            )
        gs = await self.session.join_queue(
            char_id,
            mode,
            wait_limit_sec=wait_limit_sec,
            request_id=request_id,
            commitment_id=commitment_id,
            commitment_ttl=commitment_ttl,
        )
        request = await self.session.get_request_meta(char_id)
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.SEARCHING,
            mode=mode,
            queue_request_id=request.request_id if request else request_id,
            active_match_id="",
            combat_id="",
            metadata={"queue_type": "ranked", "wait_limit_sec": wait_limit_sec, "commitment_id": commitment_id},
        )
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.SEARCHING,
            mode=mode,
            title=ArenaResources.SEARCHING_TITLE,
            description=ArenaResources.SEARCHING_DESCRIPTION,
            gs=gs,
            buttons=ArenaResources.get_searching_buttons(mode),
            metadata={
                "queue_type": "ranked",
                "commitment_status": "ready",
                "commitment_ttl": commitment_ttl,
                "wait_limit_sec": wait_limit_sec,
            },
        )

    async def start_shadow(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        runtime_session = await self._ensure_runtime_session(char_id)
        request_id = f"arena-shadow:{uuid.uuid4().hex[:12]}"
        commitment_ttl = self.SHADOW_SESSION_TTL_SEC + ARENA_COMMITMENT_GRACE_SEC
        commitment_id = await self.integrator.create_combat_commitment(
            request_id=request_id,
            char_id=char_id,
            ttl=commitment_ttl,
        )
        if not commitment_id:
            await self.session.set_runtime_screen(
                runtime_session,
                ArenaScreenEnum.MODE_MENU,
                mode=mode,
                metadata={"commitment_status": "failed", "battle_type": "shadow"},
            )
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.MODE_MENU,
                mode=mode,
                title="Тень недоступна",
                description="Арена не смогла зафиксировать боевую заявку для тренировки.",
                buttons=ArenaResources.get_mode_buttons(mode),
                metadata={"commitment_status": "failed", "battle_type": "shadow"},
            )
        match = await self._create_shadow_training_request(char_id, mode, commitment_id=commitment_id)
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.COMBAT_PENDING,
            mode=mode,
            active_match_id=match.arena_session_id,
            metadata={"battle_type": match.battle_type},
        )
        return self._pending_payload(match)

    async def check_match(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        runtime_session = await self._ensure_runtime_session(char_id)
        existing = await self.session.get_match_for_char(char_id)
        if existing is not None:
            await self.session.set_runtime_screen(
                runtime_session,
                ArenaScreenEnum.COMBAT_PENDING
                if not (existing.battle_type == "shadow" and existing.metadata.get("awaiting_player_choice"))
                else ArenaScreenEnum.SHADOW_OFFER,
                mode=existing.mode,
                active_match_id=existing.arena_session_id,
                combat_id=existing.combat_id or "",
                metadata={"battle_type": existing.battle_type},
            )
            if existing.battle_type == "shadow" and existing.metadata.get("awaiting_player_choice"):
                return self._shadow_offer_payload(existing)
            return self._pending_payload(existing)

        lock_token = await self.session.acquire_match_lock(char_id)
        if lock_token is None:
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.SEARCHING,
                mode=mode,
                title=ArenaResources.SEARCHING_TITLE,
                description="Арена уже проверяет текущую заявку. Повторный импульс пропущен.",
                wait_time_sec=0,
                buttons=ArenaResources.get_searching_buttons(mode),
                metadata={"match_lock": "busy"},
            )

        try:
            existing = await self.session.get_match_for_char(char_id)
            if existing is not None:
                await self.session.set_runtime_screen(
                    runtime_session,
                    ArenaScreenEnum.COMBAT_PENDING
                    if not (existing.battle_type == "shadow" and existing.metadata.get("awaiting_player_choice"))
                    else ArenaScreenEnum.SHADOW_OFFER,
                    mode=existing.mode,
                    active_match_id=existing.arena_session_id,
                    combat_id=existing.combat_id or "",
                    metadata={"battle_type": existing.battle_type},
                )
                if existing.battle_type == "shadow" and existing.metadata.get("awaiting_player_choice"):
                    return self._shadow_offer_payload(existing)
                return self._pending_payload(existing)

            request = await self.session.get_request_meta(char_id)
            if request is None:
                await self.session.set_runtime_screen(runtime_session, ArenaScreenEnum.MAIN_MENU, mode=None)
                return await self.get_main_menu()

            opponent_id = await self.session.find_opponent(char_id, mode)
            if opponent_id is not None:
                match = await self._create_combat_request(char_id, opponent_id, mode, battle_type="pvp")
                await self.session.set_runtime_screen(
                    runtime_session,
                    ArenaScreenEnum.COMBAT_PENDING,
                    mode=mode,
                    queue_request_id=request.request_id,
                    active_match_id=match.arena_session_id,
                    metadata={"battle_type": match.battle_type},
                )
                return self._pending_payload(match)

            wait_time = int(time.time() - request.start_time)
            if wait_time >= request.wait_limit_sec:
                await self.session.leave_queue(char_id, mode)
                await self.session.set_runtime_screen(runtime_session, ArenaScreenEnum.MODE_MENU, mode=mode)
                return ArenaUIPayloadDTO(
                    screen=ArenaScreenEnum.MODE_MENU,
                    mode=mode,
                    title="Противник не найден",
                    description="Лимит ожидания истек. Можно повторить ранговый поиск или начать тренировку с тенью.",
                    buttons=ArenaResources.get_mode_buttons(mode),
                    metadata={"queue_type": "ranked", "wait_limit_sec": request.wait_limit_sec},
                )

            await self.session.set_runtime_screen(
                runtime_session,
                ArenaScreenEnum.SEARCHING,
                mode=mode,
                queue_request_id=request.request_id,
                metadata={"queue_type": "ranked", "wait_limit_sec": request.wait_limit_sec},
            )
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.SEARCHING,
                mode=mode,
                title=ArenaResources.SEARCHING_TITLE,
                description=ArenaResources.SEARCHING_DESCRIPTION,
                gs=request.gs,
                wait_time_sec=wait_time,
                buttons=ArenaResources.get_searching_buttons(mode),
                metadata={"queue_type": "ranked", "wait_limit_sec": request.wait_limit_sec},
            )
        finally:
            await self.session.release_match_lock(char_id, lock_token)

    async def check_combat_ready(
        self,
        char_id: int,
        *,
        arena_session_id: str | None = None,
        confirm: bool = False,
    ) -> ArenaUIPayloadDTO:
        runtime_session = await self._ensure_runtime_session(char_id)
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is None:
            await self.session.set_runtime_screen(runtime_session, ArenaScreenEnum.COMBAT_FAILED)
            return self._failed_payload()

        elapsed = int(time.time() - match.created_at)
        if match.status == "ready" and match.combat_id:
            if not confirm:
                await self.session.set_runtime_screen(
                    runtime_session,
                    ArenaScreenEnum.COMBAT_PENDING,
                    mode=match.mode,
                    active_match_id=match.arena_session_id,
                    combat_id=match.combat_id,
                    metadata={"battle_type": match.battle_type},
                )
                return self._pending_payload(match, wait_time_sec=elapsed)
            await self.integrator.enter_combat(char_id, match.combat_id)
            await self.session.set_runtime_screen(
                runtime_session,
                ArenaScreenEnum.COMBAT_PENDING,
                mode=match.mode,
                active_match_id=match.arena_session_id,
                combat_id=match.combat_id,
                metadata={"battle_type": match.battle_type, "entered_combat": True},
            )
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
            await self.session.set_runtime_screen(
                runtime_session,
                ArenaScreenEnum.COMBAT_FAILED,
                mode=match.mode,
                active_match_id=match.arena_session_id,
                metadata={"battle_type": match.battle_type},
            )
            return self._failed_payload()
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.COMBAT_PENDING,
            mode=match.mode,
            active_match_id=match.arena_session_id,
            combat_id=match.combat_id or "",
            metadata={"battle_type": match.battle_type},
        )
        return self._pending_payload(match, wait_time_sec=elapsed)

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
        return await self.check_combat_ready(char_id, arena_session_id=match.arena_session_id, confirm=True)

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

    async def cancel_queue(self, char_id: int, mode: str, *, arena_session_id: str | None = None) -> ArenaUIPayloadDTO:
        runtime_session = await self._ensure_runtime_session(char_id)
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is not None:
            await self.session.delete_match(match)
        await self.session.leave_queue(char_id, mode)
        await self.session.set_runtime_screen(runtime_session, ArenaScreenEnum.MODE_MENU, mode=mode)
        return await self.get_mode_menu(mode)

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

    async def _create_combat_request(
        self,
        char_id: int,
        opponent_id: int | None,
        mode: str,
        *,
        battle_type: str,
    ) -> ArenaCombatRequestDTO:
        requester = await self.session.get_request_meta(char_id)
        opponent = await self.session.get_request_meta(opponent_id) if opponent_id is not None else None
        await self.session.prepare_match(char_id, opponent_id, mode)
        participants = {"team_1": [char_id], "team_2": [opponent_id] if opponent_id else []}
        commitments = self._participant_commitments(requester, opponent)
        match = ArenaCombatRequestDTO(
            mode=mode,
            battle_type=battle_type,  # type: ignore[arg-type]
            requested_by=char_id,
            participants=participants,
            commitments=commitments,
            ttl=self.SHADOW_SESSION_TTL_SEC if opponent_id is None else None,
            metadata={
                "shadow": opponent_id is None,
                "arena_mode": mode,
                "awaiting_player_choice": opponent_id is None,
                "awaiting_player_confirmation": True,
                "commitments": bool(commitments),
            },
        )
        await self.session.create_match(match)
        await self.integrator.request_combat_session(match)
        return match

    async def _create_shadow_training_request(
        self,
        char_id: int,
        mode: str,
        *,
        commitment_id: str,
    ) -> ArenaCombatRequestDTO:
        participants = {"team_1": [char_id], "team_2": []}
        match = ArenaCombatRequestDTO(
            mode=mode,
            battle_type="shadow",
            requested_by=char_id,
            participants=participants,
            commitments={str(char_id): commitment_id},
            ttl=self.SHADOW_SESSION_TTL_SEC,
            metadata={
                "shadow": True,
                "arena_mode": mode,
                "training": True,
                "awaiting_player_choice": False,
                "awaiting_player_confirmation": True,
                "commitments": True,
            },
        )
        await self.session.create_match(match)
        await self.integrator.request_combat_session(match)
        return match

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
            return await self.get_mode_menu(session.mode)

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
    def _participant_commitments(*requests: object | None) -> dict[str, str]:
        commitments: dict[str, str] = {}
        for request in requests:
            if request is None:
                continue
            char_id = getattr(request, "char_id", None)
            commitment_id = getattr(request, "commitment_id", None)
            if char_id is not None and commitment_id:
                commitments[str(char_id)] = str(commitment_id)
        return commitments

    @staticmethod
    def _normalize_wait_limit(wait_limit_sec: int) -> int:
        return wait_limit_sec if wait_limit_sec in {60, 180, 300} else 60

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
