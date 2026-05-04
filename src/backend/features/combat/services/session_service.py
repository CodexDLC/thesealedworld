from __future__ import annotations

import json
import time
import uuid
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto import CollectorSignalDTO, CombatMoveDTO, ExchangePayload, InstantPayload
from src.backend.features.combat.services.turn_manager import CombatTurnManager
from src.backend.features.combat.services.view_service import CombatViewService
from src.backend.infrastructure.combat.managers.session import CombatSessionManager

if TYPE_CHECKING:
    from src.shared.schemas.combat import CombatDashboardDTO, CombatLogDTO, CombatRegisterMoveRequestDTO

AFK_TIMEOUTS = {0: 60, 1: 50, 2: 40, 3: 30}
MIN_TIMEOUT = 20
LOG_PAGE_SIZE = 20


class NullArqQueue:
    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> Any | None:
        return None


class CombatSessionNotFoundError(ValueError):
    """Raised when an actor is not attached to a combat session."""


CombatSessionNotFound = CombatSessionNotFoundError


class CombatSessionService:
    """Read-only combat facade for current session state."""

    def __init__(
        self, *, store: CombatSessionManager, character_sessions: Any | None = None, arq: Any | None = None
    ) -> None:
        self.store = store
        self.character_sessions = character_sessions
        if TYPE_CHECKING:
            from src.backend.core.arq import ArqService

        self.arq: ArqService = arq or NullArqQueue()  # type: ignore
        self.view = CombatViewService()
        self.turn_manager = CombatTurnManager(self.store, self.arq)

    async def get_dashboard(self, char_id: int, *, session_id: str | None = None) -> CombatDashboardDTO:
        combat_id = session_id or await self._resolve_session_id(char_id)
        meta = await self.store.get_meta(combat_id)
        if meta is None:
            raise CombatSessionNotFoundError(f"Combat session not found: {combat_id}")

        actor_ids = CombatSessionManager.actor_ids_from_meta(meta)
        actors = await self.store.get_actors_batch(combat_id, actor_ids)
        targets = await self.store.get_targets(combat_id)
        raw_logs = await self.store.get_logs(combat_id, start=-LOG_PAGE_SIZE, stop=-1)

        return self.view.build_dashboard(
            session_id=combat_id,
            viewer_id=char_id,
            meta=meta,
            targets=targets,
            actors=actors,
            raw_logs=raw_logs,
        )

    async def register_move(
        self,
        char_id: int,
        body: CombatRegisterMoveRequestDTO,
        *,
        session_id: str | None = None,
    ) -> CombatDashboardDTO:
        combat_id = session_id or await self._resolve_session_id(char_id)
        payload = {**body.payload, **body.model_dump(mode="json", exclude={"payload"})}
        await self.register_move_request(combat_id, char_id, payload)
        return await self.get_dashboard(char_id, session_id=combat_id)

    async def register_move_request(self, session_id: str, actor_id: int, payload: dict[str, Any]) -> CombatMoveDTO:
        move = self.turn_manager._build_move_dto(actor_id, str(payload.get("action") or "attack"), payload)
        await self.turn_manager.register_move_request(session_id, actor_id, payload)
        return move

    async def register_moves_batch(self, session_id: str, actor_id: int, payloads: list[dict[str, Any]]) -> int:
        await self.turn_manager.register_moves_batch(session_id, actor_id, payloads)
        return len(payloads)

    async def get_snapshot(self, char_id: int) -> dict[str, Any]:
        session_id = await self._resolve_session_id(char_id)
        meta = await self.store.get_meta(session_id)
        if meta is None:
            raise CombatSessionNotFound(f"Combat session not found: {session_id}")
        actor_ids = CombatSessionManager.actor_ids_from_meta(meta)
        actors = await self.store.get_actors_batch(session_id, actor_ids)
        targets = await self.store.get_targets(session_id)
        moves = await self.store.get_moves_batch(session_id, actor_ids)
        return {
            "session_id": session_id,
            "meta": self._public_meta(meta),
            "actors": {actor_id: actor for actor_id, actor in actors.items() if actor is not None},
            "targets": targets,
            "moves": moves,
        }

    async def get_logs(
        self,
        char_id: int,
        *,
        page: int = 1,
        page_size: int = LOG_PAGE_SIZE,
        session_id: str | None = None,
    ) -> CombatLogDTO:
        combat_id = session_id or await self._resolve_session_id(char_id)
        page = max(1, page)
        start = (page - 1) * page_size
        stop = start + page_size - 1
        raw_logs = await self.store.get_logs(combat_id, start=start, stop=stop)
        return self.view.build_logs(
            session_id=combat_id,
            raw_logs=raw_logs,
            page=page,
            page_size=page_size,
            total=await self._count_logs(combat_id, raw_logs),
        )

    async def get_legacy_logs(self, char_id: int, *, page: int = 0, page_size: int = 50) -> dict[str, Any]:
        session_id = await self._resolve_session_id(char_id)
        start = max(0, page) * page_size
        stop = start + page_size - 1
        raw_logs = await self.store.get_logs(session_id, start=start, stop=stop)
        return {"session_id": session_id, "page": page, "items": [self._decode_log(item) for item in raw_logs]}

    async def get_history(self, char_id: int, *, session_id: str | None = None) -> CombatLogDTO:
        combat_id = session_id or await self._resolve_session_id(char_id)
        raw_logs = await self.store.get_logs(combat_id, start=0, stop=-1)
        return self.view.build_logs(
            session_id=combat_id,
            raw_logs=raw_logs,
            page=1,
            page_size=max(1, len(raw_logs)),
            total=len(raw_logs),
        )

    async def _resolve_session_id(self, char_id: int) -> str:
        if self.character_sessions is None:
            raise CombatSessionNotFoundError(f"Character {char_id} is not in active combat")
        session = await self.character_sessions.get_session(char_id)
        combat_id = ((session or {}).get("sessions") or {}).get("combat_id") if isinstance(session, dict) else None
        if not combat_id:
            raise CombatSessionNotFoundError(f"Character {char_id} is not in active combat")
        return str(combat_id)

    async def _enqueue_collector(self, session_id: str, actor_id: int, move_id: str) -> None:
        state = await self.store.get_actor_state(session_id, actor_id) or {}
        timeout = AFK_TIMEOUTS.get(int(state.get("afk_level", 0) or 0), MIN_TIMEOUT)
        immediate = CollectorSignalDTO(
            session_id=session_id, char_id=actor_id, signal_type="check_immediate", move_id=move_id
        )
        timeout_signal = CollectorSignalDTO(
            session_id=session_id, char_id=actor_id, signal_type="check_timeout", move_id=move_id
        )
        await self.arq.enqueue_job("combat_collector_task", immediate.model_dump(mode="json"))
        await self.arq.enqueue_job(
            "combat_collector_task",
            timeout_signal.model_dump(mode="json"),
            _defer_until=int(time.time() + timeout),
        )

    async def _count_logs(self, session_id: str, fallback_logs: list[str]) -> int:
        count_logs = getattr(self.store, "count_logs", None)
        if count_logs is None:
            return len(fallback_logs)
        return int(await count_logs(session_id))

    @staticmethod
    def _build_move(actor_id: int, data: dict[str, Any]) -> CombatMoveDTO:
        action = str(data.get("action") or "attack")
        if action == "use_item":
            return CombatMoveDTO(
                move_id=uuid.uuid4().hex[:8],
                char_id=actor_id,
                strategy="item",
                payload=InstantPayload(item_id=data.get("item_id"), target_id=data.get("target_id") or actor_id),
            )
        if action in {"use_skill", "cast", "instant"}:
            return CombatMoveDTO(
                move_id=uuid.uuid4().hex[:8],
                char_id=actor_id,
                strategy="instant",
                payload=InstantPayload(
                    ability_id=data.get("ability_id") or data.get("skill_id"),
                    target_id=data.get("target_id") or actor_id,
                    feint_id=data.get("feint_id"),
                ),
            )
        if action in {"leave", "surrender", "flee"}:
            return CombatMoveDTO(
                move_id=uuid.uuid4().hex[:8],
                char_id=actor_id,
                strategy="system",
                payload={"sys_action": action},
            )
        return CombatMoveDTO(
            move_id=uuid.uuid4().hex[:8],
            char_id=actor_id,
            strategy="exchange",
            payload=ExchangePayload(target_id=int(data.get("target_id") or 0), feint_id=data.get("feint_id")),
        )

    @staticmethod
    def _public_meta(meta: dict[str, Any]) -> dict[str, Any]:
        public = dict(meta)
        for field in ("teams", "actors_info", "alive_counts"):
            public[field] = CombatSessionManager.decode_json_field(public.get(field), default={})
        public["dead_actors"] = CombatSessionManager.decode_json_field(public.get("dead_actors"), default=[])
        return public

    @staticmethod
    def _decode_log(value: str) -> dict[str, Any]:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {"text": value}
        return decoded if isinstance(decoded, dict) else {"text": str(decoded)}
