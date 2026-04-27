# apps/game_core/modules/combats/session/combat_session_service.py
import json

from src.backend.database.redis.manager.account_manager import AccountManager
from src.backend.database.redis.manager.combat_manager import CombatManager
from src.backend.domains.user_features.combat.dto.combat_actor_dto import (
    ActiveAbilityDTO,
    ActiveEffectDTO,
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStatusesDTO,
    FeintHandDTO,
)
from src.backend.domains.user_features.combat.dto.combat_session_dto import (
    BattleContext,
    BattleMeta,
)

# Менеджеры и сервисы
from src.backend.domains.user_features.combat.orchestrators.handler.runtime.combat_turn_manager import CombatTurnManager
from src.backend.domains.user_features.combat.orchestrators.handler.runtime.combat_view_service import CombatViewService
from src.shared.schemas.combat import CombatDashboardDTO, CombatLogDTO


class CombatSessionService:
    """
    Facade (v3.0). Скрывает детали боевой сессии от внешних слоев.
    Работает строго по char_id персонажа.
    Отвечает за "легкое" чтение данных для клиента.
    """

    def __init__(
        self,
        account_manager: AccountManager,
        combat_manager: CombatManager,
        turn_manager: CombatTurnManager,
        view_service: CombatViewService,
    ):
        self.account_manager = account_manager
        self.combat_manager = combat_manager
        self.turn_manager = turn_manager
        self.view_service = view_service

    # --- PRIVATE HELPERS ---

    async def _resolve_session_id(self, char_id: int) -> str:
        """Резолвит сессию по персонажу."""
        sessions = await self.account_manager.get_sessions(char_id)
        if not sessions or not sessions.get("combat_id"):
            raise ValueError(f"Character {char_id} is not in active combats.")
        return str(sessions["combat_id"])

    # --- PUBLIC ACTIONS (Intents) ---

    async def register_move(self, char_id: int, payload: dict) -> CombatDashboardDTO:
        """
        Универсальная точка регистрации намерения.
        Возвращает актуальный снапшот (клиент сам решит, ждать или обновлять UI).
        """
        session_id = await self._resolve_session_id(char_id)

        # 1. Регистрируем ход (Redis + ARQ)
        await self.turn_manager.register_move_request(session_id, char_id, payload)

        # 2. Возвращаем актуальный снапшот
        return await self.get_snapshot(char_id)

    # --- READ MODELS (Lightweight Snapshot) ---

    async def get_snapshot(self, char_id: int) -> CombatDashboardDTO:
        """
        Получить актуальный экран боя.
        Собирает данные напрямую из Redis (без тяжелого ActorManager).
        """
        session_id = await self._resolve_session_id(char_id)

        # 1. Загружаем легкий контекст (2 RTT)
        context = await self._load_snapshot_context(session_id)
        if not context:
            raise ValueError(f"Session {session_id} data not found")

        # 2. Маппинг в DTO
        return self.view_service.build_dashboard_dto_from_context(char_id, context)

    async def get_logs(self, char_id: int, page: int = 0) -> CombatLogDTO:
        """Получить логи боя."""
        session_id = await self._resolve_session_id(char_id)
        raw_logs = await self.combat_manager.get_combat_log_list(session_id)
        return self.view_service.build_logs_dto(raw_logs, page)

    # --- INTERNAL LOADING LOGIC ---

    async def _load_snapshot_context(self, session_id: str) -> BattleContext | None:
        """
        Загружает минимально необходимые данные для UI.
        Meta + Targets + State + Raw(Name/Layout) + Moves + ActiveAbilities.
        """
        # 1. Load Meta (чтобы узнать участников)
        meta_raw = await self.combat_manager.get_rbc_session_meta(session_id)
        if not meta_raw:
            return None

        meta = self._parse_meta(meta_raw)

        all_actor_ids: list[int | str] = []
        for team_ids in meta.teams.values():
            all_actor_ids.extend(team_ids)

        # 2. Batch Load via Manager
        # Возвращает (targets_map, actors_data_list)
        # actors_data_list = [{"meta": ..., "loadout": ..., "statuses": ..., "moves": ...}, ...]
        targets_map, actors_data_list = await self.combat_manager.load_snapshot_data_batch(session_id, all_actor_ids)

        actors_map = {}
        moves_cache = {}

        for cid, actor_data in zip(all_actor_ids, actors_data_list, strict=False):
            if not actor_data:
                continue

            # Parse Snapshot
            actors_map[str(cid)] = self._build_light_snapshot(
                str(cid),
                self._find_team(cid, meta.teams),
                actor_data.get("meta", {}),
                actor_data.get("loadout", {}),
                actor_data.get("statuses", {}),
            )

            # Cache Moves
            if actor_data.get("moves"):
                moves_cache[str(cid)] = actor_data["moves"]

        return BattleContext(
            session_id=session_id,
            meta=meta,
            actors=actors_map,
            moves_cache=moves_cache,
            targets=targets_map,
            pending_logs=[],
        )

    # --- HELPERS ---

    def _parse_meta(self, raw: dict) -> BattleMeta:
        def d(k):
            return raw.get(k.encode()) if isinstance(k, str) else raw.get(k)

        return BattleMeta(
            active=int(d("active") or 1),
            step_counter=int(d("step_counter") or 0),
            active_actors_count=0,  # Не важно для UI
            teams=json.loads(d("teams") or "{}"),
            actors_info=json.loads(d("actors_info") or "{}"),
            battle_type=(d("battle_type") or "standard"),
            location_id=(d("location_id") or "unknown"),
        )

    def _build_light_snapshot(self, cid, team, r_meta, r_loadout, r_statuses) -> ActorSnapshot:
        """Собирает облегченный снапшот (без полной математики)."""

        # 1. Meta (State + Feints)
        # r_meta уже содержит hp, en, tokens, feints
        feints_data = r_meta.get("feints") or {}
        feints_dto = FeintHandDTO(**feints_data) if feints_data else FeintHandDTO()

        meta = ActorMetaDTO(
            id=cid,
            name=r_meta.get("name", "Unknown"),
            type=r_meta.get("type", "unknown"),
            team=team,
            template_id=r_meta.get("template_id"),
            is_ai=r_meta.get("is_ai", False),
            hp=int(r_meta.get("hp", 0)),
            max_hp=int(r_meta.get("max_hp", 100)),
            en=int(r_meta.get("en", 0)),
            max_en=int(r_meta.get("max_en", 100)),
            tactics=int(r_meta.get("tactics", 0)),
            is_dead=bool(r_meta.get("is_dead", False)),
            tokens=r_meta.get("tokens") or {},
            feints=feints_dto,  # NEW: Feints
        )

        # 2. Loadout
        loadout = ActorLoadoutDTO(
            layout=r_loadout.get("equipment_layout", {}),
            known_abilities=r_loadout.get("known_abilities", []),
            belt=r_loadout.get("belt", []),
            tags=r_loadout.get("tags", []),
        )

        # 3. Statuses
        statuses = ActorStatusesDTO(
            abilities=[ActiveAbilityDTO(**a) for a in r_statuses.get("abilities", [])],
            effects=[ActiveEffectDTO(**e) for e in r_statuses.get("effects", [])],
        )

        # 4. Raw (Stub)
        raw = ActorRawDTO(attributes={}, modifiers={})

        return ActorSnapshot(
            meta=meta,
            raw=raw,
            loadout=loadout,
            statuses=statuses,
            xp_buffer={},
        )

    def _find_team(self, cid: int | str, teams: dict) -> str:
        cid_str = str(cid)
        for t_name, members in teams.items():
            # members list can contain ints or strs
            for m in members:
                if str(m) == cid_str:
                    return t_name
        return "neutral"

    # --- LIFECYCLE ---

    async def link_players_to_session(self, char_ids: list[int], session_id: str) -> None:
        # TODO: REFACTOR: Add state transition to COMBAT here (via AccountManager.transition_to_state)
        # Currently state is changed by the caller (e.g. TutorialHandler)
        await self.account_manager.bulk_link_combat_session(char_ids, session_id)

    async def unlink_players_from_session(self, char_ids: list[int]) -> None:
        # TODO: REFACTOR: Add state transition to EXPLORATION/LOBBY here
        await self.account_manager.bulk_unlink_combat_session(char_ids)
