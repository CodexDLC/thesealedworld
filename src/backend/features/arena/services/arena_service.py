from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO
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
        await self.integrator.enter_arena(char_id)

    async def get_main_menu(self) -> ArenaUIPayloadDTO:
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MAIN_MENU,
            title=ArenaResources.MAIN_TITLE,
            description=ArenaResources.MAIN_DESCRIPTION,
            buttons=ArenaResources.get_main_buttons(),
        )

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

    async def get_group_lobby(self) -> ArenaUIPayloadDTO:
        return await self.get_mode_menu("group")

    async def group_action(self, action: str, *, item_id: str | None = None) -> ArenaUIPayloadDTO:
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
        wait_limit_sec = self._normalize_wait_limit(wait_limit_sec)
        request_id = f"arena:{uuid.uuid4().hex[:12]}"
        commitment_ttl = wait_limit_sec + ARENA_COMMITMENT_GRACE_SEC
        commitment_id = await self.integrator.create_combat_commitment(
            request_id=request_id,
            char_id=char_id,
            ttl=commitment_ttl,
        )
        if not commitment_id:
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
        request_id = f"arena-shadow:{uuid.uuid4().hex[:12]}"
        commitment_ttl = self.SHADOW_SESSION_TTL_SEC + ARENA_COMMITMENT_GRACE_SEC
        commitment_id = await self.integrator.create_combat_commitment(
            request_id=request_id,
            char_id=char_id,
            ttl=commitment_ttl,
        )
        if not commitment_id:
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.MODE_MENU,
                mode=mode,
                title="Тень недоступна",
                description="Арена не смогла зафиксировать боевую заявку для тренировки.",
                buttons=ArenaResources.get_mode_buttons(mode),
                metadata={"commitment_status": "failed", "battle_type": "shadow"},
            )
        match = await self._create_shadow_training_request(char_id, mode, commitment_id=commitment_id)
        return self._pending_payload(match)

    async def check_match(self, char_id: int, mode: str) -> ArenaUIPayloadDTO:
        existing = await self.session.get_match_for_char(char_id)
        if existing is not None:
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
            if wait_time >= request.wait_limit_sec:
                await self.session.leave_queue(char_id, mode)
                return ArenaUIPayloadDTO(
                    screen=ArenaScreenEnum.MODE_MENU,
                    mode=mode,
                    title="Противник не найден",
                    description="Лимит ожидания истек. Можно повторить ранговый поиск или начать тренировку с тенью.",
                    buttons=ArenaResources.get_mode_buttons(mode),
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
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is None:
            return self._failed_payload()

        elapsed = int(time.time() - match.created_at)
        if match.status == "ready" and match.combat_id:
            if not confirm:
                return self._pending_payload(match, wait_time_sec=elapsed)
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
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is not None:
            await self.session.delete_match(match)
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
