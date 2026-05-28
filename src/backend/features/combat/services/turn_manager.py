# apps/game_core/modules/combats/session/runtime/combat_turn_manager.py
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from loguru import logger as log
from pydantic import ValidationError

from src.backend.core.arq import ArqService
from src.backend.features.combat.dto import ExchangePayload, InstantPayload
from src.backend.features.combat.dto.action import CombatMoveDTO
from src.backend.features.combat.dto.ids import ActorIdLike, normalize_actor_id
from src.backend.features.combat.dto.worker import CollectorSignalDTO
from src.backend.features.combat.exceptions import (
    CombatFeintUnavailableError,
    CombatInvalidMovePayloadError,
    CombatTargetRequiredError,
    CombatTargetUnavailableError,
)
from src.backend.features.combat.game_config import CombatConfig
from src.backend.features.combat.integrations import CombatSessionIntegration
from src.backend.features.combat.runtime.engine.feint_service import FeintService

# Конфиг таймеров согласно документации
AFK_TIMEOUTS = {
    0: 60,  # Обычный ход
    1: 50,
    2: 40,
    3: 30,
}
MIN_TIMEOUT = 20


class CombatTurnManager:
    """Owns runtime intent registration and collector scheduling.

    ``CombatTurnManager`` is the write-side entry point for combat moves. It
    validates incoming payloads, maps them into runtime DTOs, performs atomic
    feint/target checks, writes intents into the Redis-backed move buffer, and
    schedules collector/timeout/chaos jobs in ARQ.

    It does not resolve combat math. It only prepares intent state so the
    collector/executor pipeline can process it asynchronously.
    """

    def __init__(self, combat_sessions: CombatSessionIntegration, arq_service: ArqService):
        self.combat_sessions = combat_sessions
        self.arq = arq_service

    async def register_move_request(self, session_id: str, char_id: ActorIdLike, payload: dict[str, Any]) -> None:
        """Register one player intent into the runtime buffer.

        Args:
            session_id: Active combat session id.
            char_id: Acting actor id.
            payload: Normalized move payload from the API/service layer.

        Raises:
            CombatTargetRequiredError: Exchange move was submitted without a target.
            CombatInvalidMovePayloadError: Payload cannot be mapped into a move DTO.
            CombatFeintUnavailableError: Feint cannot be consumed or afforded.
            CombatTargetUnavailableError: Target is dead or no longer available.

        Side Effects:
            - Mutates actor move buffers in Redis.
            - Consumes and may return feints atomically.
            - Enqueues immediate and delayed collector jobs.
            - Starts the chaos watchdog once combat is marked as started.
        """
        # 1. Определяем тип действия
        action_type = payload.get("action", "attack")
        if action_type in {"attack", "exchange"} and not payload.get("target_id"):
            raise CombatTargetRequiredError("Target ID is required for exchange")
        log.bind(session_id=session_id, actor_id=char_id, action=action_type).debug("TurnManagerStart")

        # 2. Получаем данные персонажа (нужен afk_level для таймера)
        # get_actor_state возвращает словарь из $.meta
        state_dict = await self.combat_sessions.get_actor_state(session_id, char_id)

        if not state_dict:
            log.bind(char_id=char_id, session_id=session_id).warning("TurnManagerActorMissing")
            afk_level = 0
        else:
            afk_level = int(state_dict.get("afk_level", 0))

        # 3. Создаем типизированную 'пулю' (DTO)
        try:
            move_dto = self._build_move_dto(char_id, action_type, payload)
        except ValidationError as e:
            log.exception("TurnManagerPayloadValidationFailed")
            raise CombatInvalidMovePayloadError("Invalid move payload structure") from e

        timeout = AFK_TIMEOUTS.get(afk_level, MIN_TIMEOUT)
        move_dto = self._with_timeout(move_dto, timeout)

        # --- FEINT VALIDATION & CONSUMPTION (ATOMIC) ---
        # Проверяем финт, если он есть в payload
        feint_id = None
        if isinstance(move_dto.payload, (ExchangePayload, InstantPayload)):
            feint_id = move_dto.payload.feint_id

        cost = None
        if feint_id:
            # Атомарно проверяем и удаляем финт из руки
            # Возвращает стоимость (dict) если успех, или None если финта нет
            cost = await self.combat_sessions.consume_feint(session_id, char_id, feint_id)

            if not cost:
                raise CombatFeintUnavailableError(
                    f"Feint {feint_id} is not in hand",
                    context={"feint_id": feint_id},
                )
            stamina_cost = FeintService.activation_stamina_cost(cost)
            actor_state = await self.combat_sessions.get_actor_state(session_id, char_id)
            actor_stamina = self._int((actor_state or {}).get("stamina"))
            if actor_stamina < stamina_cost:
                await self.combat_sessions.return_feint(session_id, char_id, feint_id, cost)
                raise CombatFeintUnavailableError(
                    f"Feint {feint_id} requires concentration",
                    context={
                        "feint_id": feint_id,
                        "required_stamina": stamina_cost,
                        "current_stamina": actor_stamina,
                    },
                )

        # 4. Записываем в буфер (Multi-Targeting / Spamming)
        if move_dto.strategy == "exchange":
            target_id = getattr(move_dto.payload, "target_id", None)
            if not target_id:
                raise CombatTargetRequiredError("Target ID is required for exchange")
            if await self._is_dead_target(session_id, target_id):
                if feint_id and cost:
                    await self.combat_sessions.return_feint(session_id, char_id, feint_id, cost)
                raise CombatTargetUnavailableError(
                    "Target is already defeated",
                    context={"target_id": str(target_id)},
                )

            success = await self.combat_sessions.register_exchange_move(
                session_id, char_id, target_id, move_dto.model_dump()
            )

            if not success:
                # Если не удалось зарегистрировать ход (цель недоступна), нужно вернуть финт!
                if feint_id and cost:
                    await self.combat_sessions.return_feint(session_id, char_id, feint_id, cost)
                targets = await self.combat_sessions.get_targets(session_id)
                log.bind(
                    session_id=session_id,
                    char_id=char_id,
                    target_id=target_id,
                    queue=targets.get(str(char_id)),
                ).warning("TurnManagerExchangeTargetRejected")
                raise CombatTargetUnavailableError(
                    "Target is not available in your queue",
                    context={"target_id": str(target_id)},
                )

        else:
            await self.combat_sessions.append_move(session_id, char_id, move_dto.strategy, move_dto.model_dump())

        await self.combat_sessions.touch_activity(session_id)

        # 5. СТАВИМ ДВЕ ЗАДАЧИ В ARQ
        signal_immediate = CollectorSignalDTO(
            session_id=session_id,
            char_id=normalize_actor_id(char_id),
            signal_type="check_immediate",
            move_id=move_dto.move_id,
        )
        await self.arq.enqueue_job("combat_collector_task", signal_immediate.model_dump())

        signal_timeout = CollectorSignalDTO(
            session_id=session_id,
            char_id=normalize_actor_id(char_id),
            signal_type="check_timeout",
            move_id=move_dto.move_id,
        )
        await self.arq.enqueue_job(
            "combat_collector_task", signal_timeout.model_dump(), _defer_until=self._defer_after(timeout)
        )
        await self._enqueue_chaos_watchdog_if_started(session_id)

        log.bind(
            session_id=session_id,
            actor_id=char_id,
            move_id=move_dto.move_id,
            action=action_type,
            strategy=move_dto.strategy,
            timeout_sec=timeout,
        ).info("TurnManagerAccepted")

    async def register_moves_batch(self, session_id: str, char_id: ActorIdLike, payloads: list[dict[str, Any]]) -> None:
        """Register multiple intents at once, primarily for AI actors.

        Args:
            session_id: Active combat session id.
            char_id: Acting actor id.
            payloads: List of normalized move payloads to register.

        Side Effects:
            - Performs atomic exchange registration with target queue removal.
            - Writes non-exchange intents into the move buffer.
            - Enqueues collector and delayed timeout jobs for accepted moves.
        """
        if not payloads:
            return

        timeout = 60
        exchange_moves_data = []
        other_moves_dtos = []
        # Per-move feint bookkeeping for refunds. Key: move_id (str). Value:
        # (feint_id, cost) consumed for that move. Used after batch registration
        # to return feints whose move_id was not accepted by the atomic Lua
        # script (e.g. target died between consume_feint and Redis script).
        consumed_feints: dict[str, tuple[str, dict[str, int]]] = {}

        # 1. Build DTOs and Separate.
        #
        # IMPORTANT: feint consumption runs BEFORE the move is appended to
        # any batch list. Otherwise a failed consume_feint (race / stale AI
        # task / duplicate) would leave the move in ``exchange_moves_data``
        # and ``register_moves_batch`` would happily register an exchange
        # whose feint was never consumed. Mirrors the single-move
        # ``register_move_request`` ordering above.
        for payload in payloads:
            action_type = payload.get("action", "attack")
            try:
                move_dto = self._with_timeout(self._build_move_dto(char_id, action_type, payload), timeout)
            except ValidationError:
                continue

            # --- FEINT CONSUMPTION (AI) — run first ---
            feint_id = None
            if isinstance(move_dto.payload, (ExchangePayload, InstantPayload)):
                feint_id = move_dto.payload.feint_id

            consumed_cost: dict[str, int] | None = None
            if feint_id:
                consumed_cost = await self.combat_sessions.consume_feint(session_id, char_id, feint_id)
                if not consumed_cost:
                    log.bind(feint_id=feint_id).warning("TurnManagerAiMissingFeint")
                    continue  # skip this move — feint was not consumed

            if move_dto.strategy == "exchange":
                target_id = getattr(move_dto.payload, "target_id", None)
                if target_id:
                    exchange_moves_data.append(
                        {
                            "move_json": move_dto.model_dump_json(),
                            "target_id": target_id,
                            "strategy": move_dto.strategy,
                            "move_id": move_dto.move_id,
                        }
                    )
                    if feint_id and consumed_cost:
                        consumed_feints[str(move_dto.move_id)] = (feint_id, dict(consumed_cost))
            else:
                # Instant / Item
                other_moves_dtos.append(move_dto)
                if feint_id and consumed_cost:
                    consumed_feints[str(move_dto.move_id)] = (feint_id, dict(consumed_cost))

        accepted_move_ids: list[str] = []

        # 2. Process Exchange Moves (Atomic Lua with POP)
        if exchange_moves_data:
            accepted_move_ids.extend(
                await self.combat_sessions.register_moves_batch(session_id, char_id, exchange_moves_data)
            )

        # 3. Process Other Moves (Pipeline without POP)
        if other_moves_dtos:
            await self.combat_sessions.append_moves_batch(session_id, char_id, other_moves_dtos)
            accepted_move_ids.extend(str(move.move_id) for move in other_moves_dtos)

        # 3a. Refund feints for moves whose move_id was not accepted by the
        #     atomic Lua script. consume_feint already ran for these but the
        #     intent was rejected (e.g. target died between consume and Lua).
        if consumed_feints:
            accepted_set = {str(mid) for mid in accepted_move_ids}
            for move_id, (feint_id, cost) in consumed_feints.items():
                if move_id in accepted_set:
                    continue
                try:
                    await self.combat_sessions.return_feint(session_id, char_id, feint_id, cost)
                except Exception:  # noqa: BLE001 — refund is best-effort; never break the response
                    log.bind(feint_id=feint_id, move_id=move_id).exception("TurnManagerBatchRefundFailed")
                else:
                    log.bind(feint_id=feint_id, move_id=move_id).warning("TurnManagerBatchRefundedFeint")

        # 4. Signals (Immediate + Timeout)
        if accepted_move_ids:
            await self.combat_sessions.touch_activity(session_id)

            # A. Immediate
            signal_immediate = CollectorSignalDTO(
                session_id=session_id,
                char_id=normalize_actor_id(char_id),
                signal_type="check_immediate",
                move_id="batch",
            )
            await self.arq.enqueue_job("combat_collector_task", signal_immediate.model_dump())

            # B. Timeout (Force Attack). Each timeout is tied to a concrete
            # move_id, matching single-move registration and preventing stale
            # batch timeouts from forcing newer AI intents.
            for move_id in accepted_move_ids:
                signal_timeout = CollectorSignalDTO(
                    session_id=session_id,
                    char_id=normalize_actor_id(char_id),
                    signal_type="check_timeout",
                    move_id=move_id,
                )
                await self.arq.enqueue_job(
                    "combat_collector_task", signal_timeout.model_dump(), _defer_until=self._defer_after(timeout)
                )

            await self._enqueue_chaos_watchdog_if_started(session_id)

            log.bind(
                session_id=session_id,
                actor_id=char_id,
                accepted_count=len(accepted_move_ids),
                requested_count=len(payloads),
                timeout_sec=timeout,
            ).info("TurnManagerBatchAccepted")
        else:
            log.bind(char_id=char_id).warning("TurnManagerBatchEmpty")

    def _build_move_dto(self, char_id: ActorIdLike, action: str, data: dict) -> CombatMoveDTO:
        """Map a public action payload into the canonical runtime move DTO."""
        strategy: Literal["exchange", "item", "instant", "system"] = "exchange"
        validated_payload: ExchangePayload | InstantPayload | dict[str, Any] = {}

        if action == "use_item":
            strategy = "item"
            # ItemPayload пока не обновляли, используем InstantPayload как заглушку или словарь
            validated_payload = InstantPayload(
                item_id=int(data.get("item_id", 0)), target_id=data.get("target_id", char_id)
            )
        elif action in ("use_skill", "cast", "instant"):
            strategy = "instant"
            validated_payload = InstantPayload(
                ability_id=data.get("ability_id") or data.get("skill_id"),
                target_id=data.get("target_id", char_id),
                feint_id=data.get("feint_id"),
            )
        elif action in ("leave", "surrender", "flee"):
            strategy = "system"
            validated_payload = {"sys_action": action}
        else:
            # По умолчанию - боевой размен (attack, defend, etc.)
            strategy = "exchange"
            validated_payload = ExchangePayload(
                target_id=normalize_actor_id(data.get("target_id") or "0"),
                feint_id=data.get("feint_id"),
            )

        return CombatMoveDTO(
            move_id=str(uuid.uuid4())[:8],
            char_id=normalize_actor_id(char_id),
            strategy=strategy,
            payload=validated_payload,
        )

    @staticmethod
    def _with_timeout(move: CombatMoveDTO, timeout_seconds: int) -> CombatMoveDTO:
        """Attach registration and forced-timeout timestamps to a move DTO."""
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        timeout_ms = max(0, int(timeout_seconds * 1000))
        return move.model_copy(
            update={
                "registered_at_ms": now_ms,
                "timeout_ms": timeout_ms,
                "force_attack_at_ms": now_ms + timeout_ms,
            }
        )

    async def _enqueue_chaos_watchdog_if_started(self, session_id: str) -> None:
        """Start the chaos watchdog once for a combat that just became active."""
        started = await self.combat_sessions.mark_started_and_refresh_ttl(session_id)
        if not started:
            return
        await self.arq.enqueue_job(
            "chaos_check_task",
            session_id,
            _defer_until=self._defer_after(int(CombatConfig.CHAOS_FIRST_CHECK_DELAY_SECONDS)),
        )

    async def _is_dead_target(self, session_id: str, target_id: ActorIdLike) -> bool:
        """Return whether the target is already dead in runtime state."""
        state = await self.combat_sessions.get_actor_state(session_id, target_id)
        if not isinstance(state, dict):
            return False
        if bool(state.get("is_dead")):
            return True
        try:
            return int(state.get("hp", 1) or 0) <= 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _defer_after(seconds: int) -> datetime:
        return datetime.now(UTC) + timedelta(seconds=seconds)

    @staticmethod
    def _int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0
