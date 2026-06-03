from __future__ import annotations

import contextlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from src.backend.features.combat.dto import CollectorSignalDTO, CombatMoveDTO, ExchangePayload, InstantPayload
from src.backend.features.combat.dto.ids import normalize_actor_id
from src.backend.features.combat.exceptions import CombatFeintUnavailableError, CombatSessionNotFoundError
from src.backend.features.combat.integrations import CombatSessionIntegration
from src.backend.features.combat.services.result_archive_service import CombatResultArchiveService
from src.backend.features.combat.services.turn_manager import CombatTurnManager
from src.backend.features.combat.services.view_service import CombatViewService
from src.shared.enums import CoreDomain
from src.shared.schemas.combat import CombatResultActionDTO, CombatResultDTO
from src.shared.schemas.response import StateTransitionDTO

if TYPE_CHECKING:
    from src.backend.features.combat.integrations import CombatSystemIntegrator
    from src.shared.schemas.combat import (
        CombatDashboardDTO,
        CombatLogDTO,
        CombatPinFeintRequestDTO,
        CombatRegisterMoveRequestDTO,
    )

AFK_TIMEOUTS = {0: 60, 1: 45, 2: 30}
MIN_TIMEOUT = 20
LOG_PAGE_SIZE = 20


class NullArqQueue:
    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> Any | None:
        return None


CombatSessionNotFound = CombatSessionNotFoundError


class CombatSessionService:
    """High-level combat session facade for API/orchestrator use cases.

    The service owns browser-facing runtime use cases such as loading the
    current dashboard, registering player intents, pinning feints, resolving
    archived results, and transitioning out of post-combat state.

    It delegates:
        - intent queueing to ``CombatTurnManager``
        - live view assembly to ``CombatViewService``
        - runtime/Redis access to ``CombatSessionIntegration``
        - archived result reconstruction to ``CombatResultArchiveService``
    """

    def __init__(
        self,
        *,
        store: CombatSessionIntegration,
        system_integrator: CombatSystemIntegrator,
        arq: Any | None = None,
        game_config: Any | None = None,
    ) -> None:
        self.store = store
        self.system_integrator = system_integrator
        self._game_config = game_config
        if TYPE_CHECKING:
            from src.backend.core.arq import ArqService

        self.arq: ArqService = arq or NullArqQueue()  # type: ignore
        self.game_config = game_config
        self.result_archive = CombatResultArchiveService()
        self.view = CombatViewService()
        self.turn_manager = CombatTurnManager(self.store, self.arq, game_config)

    async def get_dashboard(self, char_id: int, *, session_id: str | None = None) -> CombatDashboardDTO:
        """Build the live combat dashboard from runtime session state.

        Args:
            char_id: Viewing player character.
            session_id: Optional resolved combat session id.

        Returns:
            A frontend-ready combat dashboard built from runtime actors, targets,
            moves, and recent grouped logs.
        """
        combat_id = session_id or await self._resolve_session_id(char_id)
        meta = await self.store.get_meta(combat_id)
        if meta is None:
            raise CombatSessionNotFoundError(f"Combat session not found: {combat_id}")

        actor_ids = self._actor_ids_from_meta(meta)
        actors = await self.store.get_actors_batch(combat_id, actor_ids)
        targets = await self._get_targets(combat_id)
        moves = await self.store.get_moves_batch(combat_id, actor_ids)
        await self._seed_initial_ai_turns(combat_id, char_id, meta=meta, actors=actors, targets=targets, moves=moves)
        all_logs_by_turn = await self._get_logs_by_turn(combat_id)
        raw_logs_by_turn = self._slice_log_turns_from_end(all_logs_by_turn, page=1, page_size=LOG_PAGE_SIZE)
        total_logs = len(all_logs_by_turn)

        return self.view.build_dashboard(
            session_id=combat_id,
            viewer_id=char_id,
            meta=meta,
            targets=targets,
            moves=moves,
            actors=actors,
            raw_logs=[],
            raw_logs_by_turn=raw_logs_by_turn,
            total_logs=total_logs,
        )

    async def _seed_initial_ai_turns(
        self,
        session_id: str,
        viewer_id: int,
        *,
        meta: dict[str, Any],
        actors: dict[str, Any],
        targets: dict[str, list[Any]],
        moves: dict[str, Any],
    ) -> None:
        seeded = await self.store.seed_initial_ai_turns_on_dashboard(
            session_id=session_id,
            viewer_id=viewer_id,
            meta=meta,
            actors=actors,
            targets=targets,
            moves=moves,
        )
        if not seeded:
            return
        signal = CollectorSignalDTO(
            session_id=session_id,
            char_id=normalize_actor_id(viewer_id),
            signal_type="heartbeat",
            move_id="initial_ai_seed",
        )
        await self.arq.enqueue_job("combat_collector_task", signal.model_dump(mode="json"))

    async def register_move(
        self,
        char_id: int,
        body: CombatRegisterMoveRequestDTO,
        *,
        session_id: str | None = None,
    ) -> CombatDashboardDTO:
        """Register one browser/API move request against the live combat.

        The service delegates semantic move registration to ``CombatTurnManager``
        and then waits briefly for collector/executor workers to settle a fresh
        dashboard view.

        Args:
            char_id: Acting player character.
            body: Public combat move request.
            session_id: Optional resolved combat session id.

        Returns:
            The refreshed live combat dashboard after the request is accepted.
        """
        combat_id = session_id or await self._resolve_session_id(char_id)
        payload = {**body.payload, **body.model_dump(mode="json", exclude={"payload"})}
        await self.register_move_request(combat_id, char_id, payload)
        return await self.get_dashboard(char_id, session_id=combat_id)

    async def pin_feint(
        self,
        char_id: int,
        body: CombatPinFeintRequestDTO,
        *,
        session_id: str | None = None,
    ) -> CombatDashboardDTO:
        """Pin or unpin a feint inside the live runtime hand state."""
        combat_id = session_id or await self._resolve_session_id(char_id)
        success = await self.store.pin_feint(combat_id, char_id, body.feint_id)
        if not success:
            raise CombatFeintUnavailableError("Feint is not in hand", context={"feint_id": body.feint_id})
        return await self.get_dashboard(char_id, session_id=combat_id)

    async def register_move_request(self, session_id: str, actor_id: int, payload: dict[str, Any]) -> CombatMoveDTO:
        """Translate a public move payload into the runtime intent buffer.

        Args:
            session_id: Active combat session id.
            actor_id: Acting character id.
            payload: Raw move payload after request normalization.

        Returns:
            The runtime move DTO shape that was accepted for registration.

        Side Effects:
            Enqueues collector jobs through ``CombatTurnManager``.
        """
        move = self.turn_manager._build_move_dto(actor_id, str(payload.get("action") or "attack"), payload)
        await self.turn_manager.register_move_request(session_id, actor_id, payload)
        return move

    async def register_moves_batch(self, session_id: str, actor_id: int, payloads: list[dict[str, Any]]) -> int:
        """Register multiple runtime intents, primarily for AI actors."""
        await self.turn_manager.register_moves_batch(session_id, actor_id, payloads)
        return len(payloads)

    async def get_snapshot(self, char_id: int) -> dict[str, Any]:
        session_id = await self._resolve_session_id(char_id)
        meta = await self.store.get_meta(session_id)
        if meta is None:
            raise CombatSessionNotFound(f"Combat session not found: {session_id}")
        actor_ids = self._actor_ids_from_meta(meta)
        actors = await self.store.get_actors_batch(session_id, actor_ids)
        targets = await self._get_targets(session_id)
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
        """Return paginated combat logs from live or archived runtime storage."""
        combat_id = session_id
        if not combat_id:
            try:
                combat_id = await self._resolve_session_id(char_id)
            except CombatSessionNotFoundError:
                combat_id = await self._resolve_finalization_id(char_id)
                if not combat_id:
                    raise
        page = max(1, page)
        page_size = max(1, page_size)
        all_logs_by_turn = await self._get_logs_by_turn(combat_id)
        total = len(all_logs_by_turn)
        selected_logs_by_turn = self._slice_log_turns_from_end(all_logs_by_turn, page=page, page_size=page_size)
        return self.view.build_logs(
            session_id=combat_id,
            raw_logs=[],
            raw_logs_by_turn=selected_logs_by_turn,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get_archived_result(
        self,
        char_id: int,
        *,
        reason: str = "combat_session_not_found",
    ) -> CombatResultDTO:
        result = await self.find_archived_result(char_id, reason=reason)
        if result is not None:
            return result

        combat_id = await self.system_integrator.resolve_combat_session_for_character(char_id)
        finalization_id = await self._resolve_finalization_id(char_id)
        target_state = await self.system_integrator.resolve_return_state_for_character(char_id)
        return await self.result_archive.get_result_for_character(
            char_id,
            combat_id=finalization_id or combat_id,
            reason=reason,
            target_state=target_state,
        )

    async def find_archived_result(
        self,
        char_id: int,
        *,
        reason: str = "combat_session_not_found",
    ) -> CombatResultDTO | None:
        """Resolve a finished combat result from finalization or runtime history."""
        combat_id = await self.system_integrator.resolve_combat_session_for_character(char_id)
        finalization_id = await self._resolve_finalization_id(char_id)
        target_state = await self.system_integrator.resolve_return_state_for_character(char_id)
        finalization = await self.result_archive.load_finalization_for_character(
            self.store,
            char_id,
            combat_id=combat_id,
            finalization_id=finalization_id,
        )
        if finalization is not None:
            result = self.result_archive.build_result_from_finalization(
                finalization,
                char_id=char_id,
                reason=reason,
                target_state=target_state,
            )
            await self._mark_finalized_if_needed(char_id, result.combat_id, finalization_id=finalization_id)
            return result
        runtime_result = await self._build_runtime_history_result(
            char_id,
            combat_id=combat_id,
            reason=reason,
            target_state=target_state,
        )
        if runtime_result is not None:
            await self._mark_finalized_if_needed(char_id, runtime_result.combat_id, finalization_id=finalization_id)
            return runtime_result
        return None

    async def recover_missing_combat_transition(
        self,
        char_id: int,
        *,
        reason: str,
        combat_id: str | None = None,
    ) -> StateTransitionDTO:
        target = await self.system_integrator.recover_missing_combat_session(char_id, combat_id=combat_id)
        target_state = self._core_domain(target)
        return StateTransitionDTO(
            char_id=char_id,
            target_state=target_state,
            reason=reason,
            combat_id=combat_id,
        )

    async def continue_result(self, char_id: int) -> StateTransitionDTO:
        """Complete the post-combat result flow and return the next game state."""
        current_finalization_id = await self._resolve_current_finalization_id(char_id)
        combat_id = current_finalization_id or await self._resolve_latest_finalization_id(char_id)
        post_resolver = getattr(self.system_integrator, "resolve_post_combat_for_character", None)
        post_combat = await post_resolver(char_id) if post_resolver is not None else None
        target = await self.system_integrator.complete_combat_session_return(
            char_id,
            combat_id=current_finalization_id,
        )
        clear_latest = getattr(self.store, "clear_latest_finalization_id_for_character", None)
        if clear_latest is not None:
            with contextlib.suppress(Exception):
                await clear_latest(char_id)
        target_state = self._core_domain(target)
        return StateTransitionDTO(
            char_id=char_id,
            target_state=target_state,
            reason="combat_result_continued",
            combat_id=combat_id,
            metadata={"post_combat": post_combat} if post_combat else None,
        )

    async def get_history(self, char_id: int, *, session_id: str | None = None) -> CombatLogDTO:
        combat_id = session_id or await self._resolve_session_id(char_id)
        raw_logs_by_turn = await self._get_logs_by_turn(combat_id)
        return self.view.build_logs(
            session_id=combat_id,
            raw_logs=[],
            raw_logs_by_turn=raw_logs_by_turn,
            page=1,
            page_size=max(1, len(raw_logs_by_turn)),
            total=len(raw_logs_by_turn),
        )

    async def _resolve_session_id(self, char_id: int) -> str:
        combat_id = await self.system_integrator.resolve_combat_session_for_character(char_id)
        if not combat_id:
            raise CombatSessionNotFoundError(f"Character {char_id} is not in active combat")
        return combat_id

    async def _resolve_finalization_id(self, char_id: int) -> str | None:
        finalization_id = await self._resolve_current_finalization_id(char_id)
        if finalization_id:
            return finalization_id
        return await self._resolve_latest_finalization_id(char_id)

    async def _resolve_current_finalization_id(self, char_id: int) -> str | None:
        resolver = getattr(self.system_integrator, "resolve_combat_finalization_for_character", None)
        return await resolver(char_id) if resolver is not None else None

    async def _resolve_latest_finalization_id(self, char_id: int) -> str | None:
        latest = getattr(self.store, "get_latest_finalization_id_for_character", None)
        if latest is None:
            return None
        return await latest(char_id)

    async def _mark_finalized_if_needed(
        self,
        char_id: int,
        combat_id: str | None,
        *,
        finalization_id: str | None,
    ) -> None:
        if finalization_id or not combat_id:
            return
        marker = getattr(self.system_integrator, "mark_combat_finalized", None)
        if marker is not None:
            await marker(char_id, combat_id)

    @staticmethod
    def _core_domain(value: str | None) -> CoreDomain:
        if not value:
            return CoreDomain.EXPLORATION
        try:
            return CoreDomain(str(value))
        except ValueError:
            return CoreDomain.EXPLORATION

    async def _enqueue_collector(self, session_id: str, actor_id: int, move_id: str) -> None:
        state = await self.store.get_actor_state(session_id, actor_id) or {}
        min_timeout = 20.0
        if self._game_config is not None:
            min_timeout = await self._game_config.get_float("combat", "MIN_TIMEOUT", default=20.0)
        timeout = AFK_TIMEOUTS.get(int(state.get("afk_level", 0) or 0), min_timeout)
        immediate = CollectorSignalDTO(
            session_id=session_id,
            char_id=normalize_actor_id(actor_id),
            signal_type="check_immediate",
            move_id=move_id,
        )
        timeout_signal = CollectorSignalDTO(
            session_id=session_id,
            char_id=normalize_actor_id(actor_id),
            signal_type="check_timeout",
            move_id=move_id,
        )
        await self.arq.enqueue_job("combat_collector_task", immediate.model_dump(mode="json"))
        await self.arq.enqueue_job(
            "combat_collector_task",
            timeout_signal.model_dump(mode="json"),
            _defer_until=datetime.now(UTC) + timedelta(seconds=timeout),
        )

    async def _count_logs(self, session_id: str, fallback_logs: list[str]) -> int:
        count_logs = getattr(self.store, "count_logs", None)
        if count_logs is not None:
            return int(await count_logs(session_id))
        if fallback_logs:
            return len(fallback_logs)
        return len(await self.store.get_logs(session_id, start=0, stop=-1))

    async def _get_logs_by_turn(self, session_id: str) -> dict[str, list[str]]:
        get_logs_by_turn = getattr(self.store, "get_logs_by_turn", None)
        if get_logs_by_turn is not None:
            return dict(await get_logs_by_turn(session_id))
        raw_logs = await self.store.get_logs(session_id, start=0, stop=-1)
        return self._group_raw_logs_by_turn(raw_logs)

    async def _count_log_turns(self, session_id: str, fallback_logs_by_turn: dict[str, list[str]]) -> int:
        if fallback_logs_by_turn:
            return len(fallback_logs_by_turn)
        return len(await self._get_logs_by_turn(session_id))

    async def _build_runtime_history_result(
        self,
        char_id: int,
        *,
        combat_id: str | None,
        reason: str,
        target_state: str,
    ) -> CombatResultDTO | None:
        if not combat_id:
            return None
        try:
            meta = await self.store.get_meta(combat_id)
        except Exception:
            meta = None
        if not meta or not self._is_finished_meta(meta):
            return None

        try:
            logs_by_turn = await self._get_logs_by_turn(combat_id)
        except Exception:
            logs_by_turn = {}

        winner = self._meta_string(meta.get("winner")) or self._inferred_winner_from_meta(meta)
        viewer_team = self._team_for_actor(meta, char_id)
        outcome = self._outcome_for_actor(winner=winner, viewer_team=viewer_team)
        last_turn = self._last_log_turn(logs_by_turn)
        summary = self._result_summary(outcome=outcome, winner=winner, last_turn=last_turn)
        return CombatResultDTO(
            combat_id=combat_id,
            char_id=char_id,
            status="finished",
            outcome=outcome,
            title=self._result_title(outcome),
            message="Бой завершен. Живой runtime-снимок уже закрыт.",
            summary=summary,
            reason=reason,
            archived=True,
            metadata={
                "source": "combat_runtime_history",
                "winner": winner,
                "viewer_team": viewer_team,
                "turns": len(logs_by_turn),
                "last_turn": last_turn,
            },
            primary_action=CombatResultActionDTO(
                label="Продолжить",
                action="navigate",
                target_state=target_state,
            ),
        )

    @staticmethod
    def _slice_log_turns_from_end(
        logs_by_turn: dict[str, list[str]], *, page: int, page_size: int
    ) -> dict[str, list[str]]:
        items = sorted(logs_by_turn.items(), key=lambda item: CombatSessionService._turn_sort_key(item[0]))
        stop = max(len(items) - ((page - 1) * page_size), 0)
        start = max(stop - page_size, 0)
        return dict(items[start:stop])

    @staticmethod
    def _turn_sort_key(turn: str) -> tuple[int, str]:
        with contextlib.suppress(TypeError, ValueError):
            return (int(turn), str(turn))
        return (0, str(turn))

    @staticmethod
    def _group_raw_logs_by_turn(raw_logs: list[str]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for index, raw in enumerate(raw_logs):
            turn = str(index)
            with contextlib.suppress(json.JSONDecodeError):
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    turn = str(parsed.get("global_turn", index))
            grouped.setdefault(turn, []).append(raw)
        return grouped

    @staticmethod
    def _is_finished_meta(meta: dict[str, Any]) -> bool:
        status = str(meta.get("status") or "").lower()
        active = str(meta.get("active") or "")
        winner = str(meta.get("winner") or "")
        return (
            status == "finished"
            or active == "0"
            or bool(winner)
            or CombatSessionService._inferred_winner_from_meta(meta) is not None
        )

    @staticmethod
    def _inferred_winner_from_meta(meta: dict[str, Any]) -> str | None:
        alive_counts = CombatSessionIntegration.decode_json_field(meta.get("alive_counts"), default={})
        if isinstance(alive_counts, dict) and alive_counts:
            alive_teams = sorted(
                str(team) for team, count in alive_counts.items() if CombatSessionService._int_meta(count) > 0
            )
            if len(alive_teams) == 1:
                return alive_teams[0]
            if not alive_teams:
                return "draw"
            return None

        teams = CombatSessionIntegration.decode_json_field(meta.get("teams"), default={})
        if not isinstance(teams, dict) or not teams:
            return None
        dead_actors = CombatSessionIntegration.decode_json_field(meta.get("dead_actors"), default=[])
        dead_actor_ids = {str(actor_id) for actor_id in dead_actors} if isinstance(dead_actors, list) else set()
        alive_teams = sorted(
            str(team)
            for team, members in teams.items()
            if isinstance(members, list) and any(str(member) not in dead_actor_ids for member in members)
        )
        if len(alive_teams) == 1:
            return alive_teams[0]
        if not alive_teams:
            return "draw"
        return None

    @staticmethod
    def _int_meta(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _meta_string(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"none", "null", "unknown"}:
            return None
        return text

    @staticmethod
    def _team_for_actor(meta: dict[str, Any], char_id: int) -> str | None:
        teams = CombatSessionIntegration.decode_json_field(meta.get("teams"), default={})
        actor_id = str(char_id)
        if not isinstance(teams, dict):
            return None
        for team, members in teams.items():
            if isinstance(members, list) and actor_id in {str(member) for member in members}:
                return str(team)
        return None

    @staticmethod
    def _outcome_for_actor(*, winner: str | None, viewer_team: str | None) -> str:
        if not winner:
            return "unknown"
        if winner == "draw":
            return "draw"
        if not viewer_team:
            return "unknown"
        return "victory" if viewer_team == winner else "defeat"

    @staticmethod
    def _result_title(outcome: str) -> str:
        titles = {
            "victory": "Победа",
            "defeat": "Поражение",
            "draw": "Ничья",
        }
        return titles.get(outcome, "Итоги боя")

    @staticmethod
    def _result_summary(*, outcome: str, winner: str | None, last_turn: int | None) -> str:
        leads = {
            "victory": "Ваша команда победила.",
            "defeat": "Ваша команда проиграла.",
            "draw": "Бой завершен ничьей.",
        }
        parts = [leads.get(outcome, "Бой завершен, но итог для персонажа не удалось определить.")]
        if winner and outcome == "unknown":
            parts.append(f"Победитель: {winner}.")
        if last_turn is not None:
            parts.append(f"Последний ход в журнале: {last_turn}.")
        return " ".join(parts)

    @staticmethod
    def _last_log_turn(logs_by_turn: dict[str, list[str]]) -> int | None:
        numeric_turns: list[int] = []
        for turn in logs_by_turn:
            with contextlib.suppress(TypeError, ValueError):
                numeric_turns.append(int(turn))
        return max(numeric_turns) if numeric_turns else None

    async def _get_targets(self, session_id: str) -> dict[str, list[Any]]:
        get_targets_map = getattr(self.store, "get_targets_map", None)
        if get_targets_map is not None:
            return await get_targets_map(session_id)
        return await self.store.get_targets(session_id)

    def _actor_ids_from_meta(self, meta: dict[str, Any]) -> list[str]:
        actor_ids_from_meta = getattr(self.store, "actor_ids_from_meta", None)
        if actor_ids_from_meta is not None:
            return actor_ids_from_meta(meta)
        return CombatSessionIntegration.actor_ids_from_meta(meta)

    @staticmethod
    def _build_move(actor_id: int | str, data: dict[str, Any]) -> CombatMoveDTO:
        action = str(data.get("action") or "attack")
        if action == "use_item":
            return CombatMoveDTO(
                move_id=uuid.uuid4().hex[:8],
                char_id=normalize_actor_id(actor_id),
                strategy="item",
                payload=InstantPayload(
                    item_id=data.get("item_id"),
                    target_id=normalize_actor_id(data.get("target_id") or actor_id),
                ),
            )
        if action in {"use_skill", "cast", "instant"}:
            return CombatMoveDTO(
                move_id=uuid.uuid4().hex[:8],
                char_id=normalize_actor_id(actor_id),
                strategy="instant",
                payload=InstantPayload(
                    ability_id=data.get("ability_id") or data.get("skill_id"),
                    target_id=normalize_actor_id(data.get("target_id") or actor_id),
                    feint_id=data.get("feint_id"),
                ),
            )
        if action in {"leave", "surrender", "flee"}:
            return CombatMoveDTO(
                move_id=uuid.uuid4().hex[:8],
                char_id=normalize_actor_id(actor_id),
                strategy="system",
                payload={"sys_action": action},
            )
        return CombatMoveDTO(
            move_id=uuid.uuid4().hex[:8],
            char_id=normalize_actor_id(actor_id),
            strategy="exchange",
            payload=ExchangePayload(
                target_id=normalize_actor_id(data.get("target_id") or "0"),
                feint_id=data.get("feint_id"),
            ),
        )

    @staticmethod
    def _public_meta(meta: dict[str, Any]) -> dict[str, Any]:
        public = dict(meta)
        for field in ("teams", "actors_info", "alive_counts"):
            public[field] = CombatSessionIntegration.decode_json_field(public.get(field), default={})
        public["dead_actors"] = CombatSessionIntegration.decode_json_field(public.get("dead_actors"), default=[])
        return public

    @staticmethod
    def _decode_log(value: str) -> dict[str, Any]:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {"text": value}
        return decoded if isinstance(decoded, dict) else {"text": str(decoded)}
