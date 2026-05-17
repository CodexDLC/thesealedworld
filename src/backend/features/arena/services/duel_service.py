from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from src.backend.features.arena.dto.session import ArenaCombatRequestDTO, ArenaRuntimeSessionDTO
from src.backend.features.arena.resources import ArenaResources
from src.backend.infrastructure.actor_commitments import ActorCommitmentManager
from src.shared.schemas.arena import ArenaModeEnum, ArenaScreenEnum, ArenaUIPayloadDTO

if TYPE_CHECKING:
    from src.backend.features.arena.services.arena_service import ArenaService

DUEL_MODE = ArenaModeEnum.ONE_VS_ONE.value
COMBAT_READY_TIMEOUT = 60
ARENA_SNAPSHOT_GRACE_SEC = 10 * 60
ARENA_COMMITMENT_GRACE_SEC = ARENA_SNAPSHOT_GRACE_SEC
DUEL_MIN_WAIT_SEC = 60
DUEL_MID_WAIT_SEC = 180
DUEL_MAX_WAIT_SEC = 300


class ArenaDuelService:
    def __init__(self, *, arena: ArenaService) -> None:
        self.arena = arena
        self.session = arena.session
        self.integrator = arena.integrator

    async def view(self, char_id: int) -> ArenaUIPayloadDTO:
        runtime_session = await self.arena.ensure_runtime_session(char_id)
        payload = await self._payload_from_runtime_session(runtime_session)
        if payload.screen == ArenaScreenEnum.MAIN_MENU:
            return await self.show_menu(char_id)
        return payload

    async def show_menu(self, char_id: int) -> ArenaUIPayloadDTO:
        runtime_session = await self.arena.ensure_runtime_session(char_id)
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.MODE_MENU,
            mode=DUEL_MODE,
            active_match_id="",
            combat_id="",
        )
        return await self.get_menu(char_id)

    async def get_menu(self, char_id: int | None = None) -> ArenaUIPayloadDTO:
        metadata = await self._mode_metadata(char_id)
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.MODE_MENU,
            mode=DUEL_MODE,
            title=ArenaResources.get_mode_title(DUEL_MODE),
            description=ArenaResources.get_mode_description(DUEL_MODE),
            buttons=ArenaResources.get_mode_buttons(DUEL_MODE),
            metadata=metadata,
        )

    async def join_queue(self, char_id: int, *, wait_limit_sec: int = 60) -> ArenaUIPayloadDTO:
        _ = wait_limit_sec
        runtime_session = await self.arena.ensure_runtime_session(char_id)
        waiting_before = await self.session.queue_waiting_count(DUEL_MODE, exclude_char_id=char_id)
        wait_limit_sec = self._wait_limit_for_queue(waiting_before)
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
                mode=DUEL_MODE,
                metadata={
                    "commitment_status": "failed",
                    "commitment_ttl": commitment_ttl,
                    "queue_waiting_count": waiting_before,
                    "wait_limit_sec": wait_limit_sec,
                },
            )
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.MODE_MENU,
                mode=DUEL_MODE,
                title="Боевая сигнатура недоступна",
                description="Арена не смогла зафиксировать боевую заявку. Повторите поиск позже.",
                buttons=ArenaResources.get_mode_buttons(DUEL_MODE),
                metadata={
                    "commitment_status": "failed",
                    "commitment_ttl": commitment_ttl,
                    "queue_waiting_count": waiting_before,
                    "wait_limit_sec": wait_limit_sec,
                },
            )
        gs = await self.session.join_queue(
            char_id,
            DUEL_MODE,
            wait_limit_sec=wait_limit_sec,
            request_id=request_id,
            commitment_id=commitment_id,
            commitment_ttl=commitment_ttl,
        )
        request = await self.session.get_request_meta(char_id)
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.SEARCHING,
            mode=DUEL_MODE,
            queue_request_id=request.request_id if request else request_id,
            active_match_id="",
            combat_id="",
            metadata={
                "queue_type": "ranked",
                "wait_limit_sec": wait_limit_sec,
                "queue_waiting_count": waiting_before + 1,
                "commitment_id": commitment_id,
            },
        )
        return ArenaUIPayloadDTO(
            screen=ArenaScreenEnum.SEARCHING,
            mode=DUEL_MODE,
            title=ArenaResources.SEARCHING_TITLE,
            description=ArenaResources.SEARCHING_DESCRIPTION,
            gs=gs,
            buttons=ArenaResources.get_searching_buttons(DUEL_MODE),
            metadata={
                "queue_type": "ranked",
                "commitment_status": "ready",
                "commitment_ttl": commitment_ttl,
                "wait_limit_sec": wait_limit_sec,
                "queue_waiting_count": waiting_before + 1,
            },
        )

    async def start_shadow(self, char_id: int) -> ArenaUIPayloadDTO:
        runtime_session = await self.arena.ensure_runtime_session(char_id)
        request_id = f"arena-shadow:{uuid.uuid4().hex[:12]}"
        commitment_ttl = self.arena.SHADOW_SESSION_TTL_SEC + ARENA_COMMITMENT_GRACE_SEC
        commitment_id = await self.integrator.create_combat_commitment(
            request_id=request_id,
            char_id=char_id,
            ttl=commitment_ttl,
        )
        if not commitment_id:
            await self.session.set_runtime_screen(
                runtime_session,
                ArenaScreenEnum.MODE_MENU,
                mode=DUEL_MODE,
                metadata={"commitment_status": "failed", "battle_type": "shadow"},
            )
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.MODE_MENU,
                mode=DUEL_MODE,
                title="Тень недоступна",
                description="Арена не смогла зафиксировать боевую заявку для тренировки.",
                buttons=ArenaResources.get_mode_buttons(DUEL_MODE),
                metadata={"commitment_status": "failed", "battle_type": "shadow"},
            )
        match = await self._create_shadow_training_request(char_id, commitment_id=commitment_id)
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.COMBAT_PENDING,
            mode=DUEL_MODE,
            active_match_id=match.arena_session_id,
            metadata={"battle_type": match.battle_type},
        )
        return self._pending_payload(match)

    async def check_match(self, char_id: int) -> ArenaUIPayloadDTO:
        runtime_session = await self.arena.ensure_runtime_session(char_id)
        existing = await self.session.get_match_for_char(char_id)
        if existing is not None:
            await self._store_existing_match_screen(runtime_session, existing)
            if existing.battle_type == "shadow" and existing.metadata.get("awaiting_player_choice"):
                return self._shadow_offer_payload(existing)
            return self._pending_payload(existing)

        lock_token = await self.session.acquire_match_lock(char_id)
        if lock_token is None:
            request = await self.session.get_request_meta(char_id)
            waiting_count = await self.session.queue_waiting_count(DUEL_MODE)
            metadata: dict[str, object] = {
                "match_lock": "busy",
                "queue_waiting_count": waiting_count,
            }
            if request is not None:
                metadata["queue_type"] = "ranked"
                metadata["wait_limit_sec"] = request.wait_limit_sec
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.SEARCHING,
                mode=DUEL_MODE,
                title=ArenaResources.SEARCHING_TITLE,
                description="Арена уже проверяет текущую заявку. Повторный импульс пропущен.",
                wait_time_sec=0,
                buttons=ArenaResources.get_searching_buttons(DUEL_MODE),
                metadata=metadata,
            )

        try:
            existing = await self.session.get_match_for_char(char_id)
            if existing is not None:
                await self._store_existing_match_screen(runtime_session, existing)
                if existing.battle_type == "shadow" and existing.metadata.get("awaiting_player_choice"):
                    return self._shadow_offer_payload(existing)
                return self._pending_payload(existing)

            request = await self.session.get_request_meta(char_id)
            if request is None:
                await self.session.set_runtime_screen(runtime_session, ArenaScreenEnum.MODE_MENU, mode=DUEL_MODE)
                return await self.get_menu(char_id)

            opponent_id = await self.session.find_opponent(char_id, DUEL_MODE)
            if opponent_id is not None:
                match = await self._create_combat_request(char_id, opponent_id, battle_type="pvp")
                await self.session.set_runtime_screen(
                    runtime_session,
                    ArenaScreenEnum.COMBAT_PENDING,
                    mode=DUEL_MODE,
                    queue_request_id=request.request_id,
                    active_match_id=match.arena_session_id,
                    metadata={"battle_type": match.battle_type},
                )
                return self._pending_payload(match)

            wait_time = int(time.time() - request.start_time)
            if wait_time >= request.wait_limit_sec:
                await self.session.leave_queue(char_id, DUEL_MODE)
                await self.session.set_runtime_screen(runtime_session, ArenaScreenEnum.MODE_MENU, mode=DUEL_MODE)
                waiting_count = await self.session.queue_waiting_count(DUEL_MODE, exclude_char_id=char_id)
                return ArenaUIPayloadDTO(
                    screen=ArenaScreenEnum.MODE_MENU,
                    mode=DUEL_MODE,
                    title="Противник не найден",
                    description="Лимит ожидания истек. В очереди нет подходящих игроков; можно повторить поиск или начать тренировку с тенью.",
                    buttons=ArenaResources.get_mode_buttons(DUEL_MODE),
                    metadata={
                        "queue_type": "ranked",
                        "wait_limit_sec": request.wait_limit_sec,
                        "queue_waiting_count": waiting_count,
                    },
                )

            waiting_count = await self.session.queue_waiting_count(DUEL_MODE)
            await self.session.set_runtime_screen(
                runtime_session,
                ArenaScreenEnum.SEARCHING,
                mode=DUEL_MODE,
                queue_request_id=request.request_id,
                metadata={
                    "queue_type": "ranked",
                    "wait_limit_sec": request.wait_limit_sec,
                    "queue_waiting_count": waiting_count,
                },
            )
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.SEARCHING,
                mode=DUEL_MODE,
                title=ArenaResources.SEARCHING_TITLE,
                description=ArenaResources.SEARCHING_DESCRIPTION,
                gs=request.gs,
                wait_time_sec=wait_time,
                buttons=ArenaResources.get_searching_buttons(DUEL_MODE),
                metadata={
                    "queue_type": "ranked",
                    "wait_limit_sec": request.wait_limit_sec,
                    "queue_waiting_count": waiting_count,
                },
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
        runtime_session = await self.arena.ensure_runtime_session(char_id)
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

    async def accept_shadow(self, char_id: int, *, arena_session_id: str | None = None) -> ArenaUIPayloadDTO:
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is None or match.battle_type != "shadow":
            return self._failed_payload()
        match.metadata["awaiting_player_choice"] = False
        match.updated_at = time.time()
        await self.session.update_match(match)
        return await self.check_combat_ready(char_id, arena_session_id=match.arena_session_id, confirm=True)

    async def continue_search(self, char_id: int, *, arena_session_id: str | None = None) -> ArenaUIPayloadDTO:
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is not None:
            await self.session.delete_match(match)
        return await self.join_queue(char_id)

    async def cancel_queue(self, char_id: int, *, arena_session_id: str | None = None) -> ArenaUIPayloadDTO:
        runtime_session = await self.arena.ensure_runtime_session(char_id)
        match = await self.session.get_match(arena_session_id) if arena_session_id else None
        if match is None:
            match = await self.session.get_match_for_char(char_id)
        if match is not None:
            await self.session.delete_match(match)
        await self.session.leave_queue(char_id, DUEL_MODE)
        await self.session.set_runtime_screen(runtime_session, ArenaScreenEnum.MODE_MENU, mode=DUEL_MODE)
        return await self.get_menu(char_id)

    async def _payload_from_runtime_session(self, session: ArenaRuntimeSessionDTO) -> ArenaUIPayloadDTO:
        match = None
        if session.active_match_id:
            match = await self.session.get_match(session.active_match_id)
        if match is None:
            match = await self.session.get_match_for_char(session.char_id)
        if match is not None:
            if await self.arena.clear_completed_entered_match(session, match):
                return await self.get_menu(session.char_id)
            if match.battle_type == "shadow" and match.metadata.get("awaiting_player_choice"):
                return self._shadow_offer_payload(match)
            return self._pending_payload(match)

        request = await self.session.get_request_meta(session.char_id)
        if request is not None and request.mode == DUEL_MODE:
            wait_time = int(time.time() - request.start_time)
            waiting_count = await self.session.queue_waiting_count(DUEL_MODE)
            return ArenaUIPayloadDTO(
                screen=ArenaScreenEnum.SEARCHING,
                mode=DUEL_MODE,
                title=ArenaResources.SEARCHING_TITLE,
                description=ArenaResources.SEARCHING_DESCRIPTION,
                gs=request.gs,
                wait_time_sec=wait_time,
                buttons=ArenaResources.get_searching_buttons(DUEL_MODE),
                metadata={
                    "queue_type": "ranked",
                    "wait_limit_sec": request.wait_limit_sec,
                    "queue_waiting_count": waiting_count,
                },
            )

        if session.screen in {ArenaScreenEnum.COMBAT_FAILED, ArenaScreenEnum.COMBAT_PENDING}:
            await self.session.set_runtime_screen(session, ArenaScreenEnum.MODE_MENU, mode=DUEL_MODE)
        return await self.get_menu(session.char_id)

    async def _store_existing_match_screen(
        self,
        runtime_session: ArenaRuntimeSessionDTO,
        match: ArenaCombatRequestDTO,
    ) -> None:
        await self.session.set_runtime_screen(
            runtime_session,
            ArenaScreenEnum.COMBAT_PENDING
            if not (match.battle_type == "shadow" and match.metadata.get("awaiting_player_choice"))
            else ArenaScreenEnum.SHADOW_OFFER,
            mode=match.mode,
            active_match_id=match.arena_session_id,
            combat_id=match.combat_id or "",
            metadata={"battle_type": match.battle_type},
        )

    async def _create_combat_request(
        self,
        char_id: int,
        opponent_id: int | None,
        *,
        battle_type: str,
    ) -> ArenaCombatRequestDTO:
        requester = await self.session.get_request_meta(char_id)
        opponent = await self.session.get_request_meta(opponent_id) if opponent_id is not None else None
        await self.session.prepare_match(char_id, opponent_id, DUEL_MODE)
        participants = {"team_1": [char_id], "team_2": [opponent_id] if opponent_id else []}
        match = ArenaCombatRequestDTO(
            mode=DUEL_MODE,
            battle_type=battle_type,  # type: ignore[arg-type]
            requested_by=char_id,
            participants=participants,
            commitments=self._participant_commitments(requester, opponent),
            ttl=self.arena.SHADOW_SESSION_TTL_SEC if opponent_id is None else None,
            metadata={
                "shadow": opponent_id is None,
                "arena_mode": DUEL_MODE,
                "awaiting_player_choice": opponent_id is None,
                "awaiting_player_confirmation": True,
                "commitments": bool(self._participant_commitments(requester, opponent)),
            },
        )
        await self.session.create_match(match)
        await self.integrator.request_combat_session(match)
        return match

    async def _create_shadow_training_request(self, char_id: int, *, commitment_id: str) -> ArenaCombatRequestDTO:
        match = ArenaCombatRequestDTO(
            mode=DUEL_MODE,
            battle_type="shadow",
            requested_by=char_id,
            participants={"team_1": [char_id], "team_2": []},
            commitments={ActorCommitmentManager.source_ref("player", char_id): commitment_id},
            ttl=self.arena.SHADOW_SESSION_TTL_SEC,
            metadata={
                "shadow": True,
                "arena_mode": DUEL_MODE,
                "training": True,
                "awaiting_player_choice": False,
                "awaiting_player_confirmation": True,
                "commitments": True,
            },
        )
        await self.session.create_match(match)
        await self.integrator.request_combat_session(match)
        return match

    @staticmethod
    def _pending_payload(
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
                commitments[ActorCommitmentManager.source_ref("player", char_id)] = str(commitment_id)
        return commitments

    async def _mode_metadata(self, char_id: int | None = None) -> dict[str, object]:
        return {
            "queue_waiting_count": await self.session.queue_waiting_count(DUEL_MODE, exclude_char_id=char_id),
            "max_wait_limit_sec": DUEL_MAX_WAIT_SEC,
        }

    @staticmethod
    def _wait_limit_for_queue(waiting_count: int) -> int:
        if waiting_count <= 0:
            return DUEL_MIN_WAIT_SEC
        if waiting_count <= 2:
            return DUEL_MID_WAIT_SEC
        return DUEL_MAX_WAIT_SEC

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
