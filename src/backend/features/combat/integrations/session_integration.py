from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

# DTOs
from src.backend.features.combat.dto.actor import (
    ActiveAbilityDTO,
    ActiveEffectDTO,
    ActorLoadoutDTO,
    ActorMetaDTO,
    ActorRawDTO,
    ActorSnapshot,
    ActorStatusesDTO,
)
from src.backend.features.combat.dto.session import (
    BattleContext,
    BattleMeta,
)

# Инфраструктура
from src.backend.infrastructure.combat.managers.session import CombatSessionManager

if TYPE_CHECKING:
    from collections.abc import Sequence

    from codex_platform.redis_service import RedisService

    from src.backend.features.combat.dto.action import CombatActionDTO


class CombatSessionIntegration:
    """
    Combat session integration facade (RBC v3.0).
    Единая точка доступа к данным боя для Коллектора и Исполнителя.
    Использует CombatSessionManager для низкоуровневых операций.
    """

    def __init__(self, combat_manager: CombatSessionManager):
        self.combat_manager = combat_manager

    @classmethod
    def from_redis(cls, redis: RedisService) -> CombatSessionIntegration:
        return cls(CombatSessionManager(redis))

    async def get_meta(self, session_id: str) -> dict[str, Any] | None:
        return await self.combat_manager.get_meta(session_id)

    async def get_raw_meta(self, session_id: str) -> dict[str, Any] | None:
        return await self.combat_manager.get_rbc_session_meta(session_id)

    async def get_actors_batch(self, session_id: str, actor_ids: list[str]) -> dict[str, Any]:
        return await self.combat_manager.get_actors_batch(session_id, actor_ids)

    async def get_targets_map(self, session_id: str) -> dict[str, list[Any]]:
        return await self.combat_manager.get_targets(session_id)

    async def get_logs(self, session_id: str, *, start: int = 0, stop: int = -1) -> list[str]:
        return await self.combat_manager.get_logs(session_id, start=start, stop=stop)

    async def get_moves_batch(self, session_id: str, actor_ids: Sequence[str | int]) -> dict[str, Any]:
        return await self.combat_manager.get_moves_batch(session_id, actor_ids)

    async def count_logs(self, session_id: str) -> int:
        count_logs = getattr(self.combat_manager, "count_logs", None)
        if count_logs is None:
            return len(await self.get_logs(session_id, start=0, stop=-1))
        return int(await count_logs(session_id))

    async def get_actor_state(self, session_id: str, actor_id: int | str) -> dict[str, Any] | None:
        return await self.combat_manager.get_actor_state(session_id, actor_id)

    async def consume_feint(self, session_id: str, actor_id: int | str, feint_id: str) -> dict[str, int] | None:
        return await self.combat_manager.consume_feint_atomic(session_id, actor_id, feint_id)

    async def return_feint(self, session_id: str, actor_id: int | str, feint_id: str, cost: dict[str, int]) -> None:
        await self.combat_manager.return_feint_to_hand(session_id, actor_id, feint_id, cost)

    async def register_exchange_move(
        self,
        session_id: str,
        actor_id: int | str,
        target_id: int,
        move_dto: dict[str, Any],
    ) -> bool:
        return await self.combat_manager.register_exchange_move_atomic(session_id, actor_id, target_id, move_dto)

    async def append_move(self, session_id: str, actor_id: int | str, strategy: str, move_dto: dict[str, Any]) -> None:
        await self.combat_manager.append_move(session_id, actor_id, strategy, move_dto)

    async def register_moves_batch(
        self,
        session_id: str,
        actor_id: int | str,
        exchange_moves_data: list[dict[str, Any]],
    ) -> int:
        return await self.combat_manager.register_moves_batch_atomic(session_id, actor_id, exchange_moves_data)

    async def append_moves_batch(self, session_id: str, actor_id: int | str, moves: list[Any]) -> None:
        await self.combat_manager.append_moves_batch(session_id, actor_id, moves)

    async def hot_join_actor(
        self,
        *,
        session_id: str,
        actor_id: int,
        team_name: str,
        actor_data: dict[str, Any],
        is_ai: bool,
    ) -> None:
        await self.combat_manager.universal_hot_join(
            session_id=session_id,
            char_id=actor_id,
            team_name=team_name,
            actor_data=actor_data,
            is_ai=is_ai,
        )

    async def add_log(self, session_id: str, text: str, tags: list[str] | None = None) -> None:
        await self.combat_manager.add_log(session_id, text, tags=tags)

    async def create_session_batch(self, session_id: str, session_data: Any, *, ttl: int) -> None:
        await self.combat_manager.create_session_batch(session_id, session_data, ttl=ttl)

    async def cleanup_session(self, session_id: str) -> None:
        await self.combat_manager.cleanup_session(session_id)

    @staticmethod
    def actor_ids_from_meta(meta: dict[str, Any]) -> list[str]:
        return CombatSessionManager.actor_ids_from_meta(meta)

    @staticmethod
    def decode_json_field(value: Any, *, default: Any) -> Any:
        return CombatSessionManager.decode_json_field(value, default=default)

    # ==========================================================================
    # 1. МЕТОДЫ ДЛЯ КОЛЛЕКТОРА (LIGHTWEIGHT)
    # ==========================================================================

    async def get_battle_meta(self, session_id: str) -> BattleMeta | None:
        """Загружает только мета-данные боя."""
        meta_raw = await self.combat_manager.get_rbc_session_meta(session_id)
        if not meta_raw:
            return None
        return self._parse_meta(meta_raw)

    async def get_intent_moves(self, session_id: str, char_ids: list[int | str]) -> dict[str, Any]:
        """
        Пакетная загрузка намерений (пуль) игроков.
        Возвращает словарь {char_id: moves_dict}.
        """
        return await self.combat_manager.get_moves_batch(session_id, char_ids)

    async def get_targets(self, session_id: str) -> dict[str, list[int]]:
        """
        Загружает очереди целей всех участников.
        Возвращает {char_id: [target_id, ...]}.
        """
        targets_map, _ = await self.combat_manager.load_snapshot_data_batch(session_id, [])
        return targets_map

    async def check_intent_exists(self, session_id: str, char_id: int | str) -> bool:
        """Быстрая проверка наличия хода."""
        return await self.combat_manager.check_move_exists(session_id, char_id)

    async def push_actions_to_queue(self, session_id: str, actions: list[CombatActionDTO]) -> None:
        """Запись резолвленных задач в системную очередь q:actions."""
        if not actions:
            return

        actions_json = [a.model_dump_json() for a in actions]
        await self.combat_manager.push_actions_batch(session_id, actions_json)

    async def get_action_queue_size(self, session_id: str) -> int:
        """Возвращает текущий размер очереди действий."""
        return await self.combat_manager.get_queue_size(session_id)

    async def load_actions_batch(self, session_id: str, batch_size: int) -> list[str]:
        """Загружает пачку действий из системной очереди без раскрытия Redis client."""
        return await self.combat_manager.load_actions_batch(session_id, batch_size)

    async def set_battle_winner(self, session_id: str, winner: str) -> None:
        """
        Устанавливает статус победы в мета-данных.
        """
        await self.combat_manager.set_winner(session_id, winner)

    async def set_winner(self, session_id: str, winner: str) -> None:
        await self.set_battle_winner(session_id, winner)

    async def transfer_actions(self, session_id: str, actions: list[CombatActionDTO]) -> None:
        """
        Атомарный перенос действий: Push в очередь + Delete из moves.
        """
        if not actions:
            return

        actions_json = []
        deletes = []

        for action in actions:
            # 1. JSON для очереди
            actions_json.append(action.model_dump_json())

            # 2. Данные для удаления (Source Move)
            deletes.append(
                {"char_id": action.move.char_id, "strategy": action.move.strategy, "move_id": action.move.move_id}
            )

            # 3. Если это Exchange, удаляем и Partner Move
            if action.partner_move:
                deletes.append(
                    {
                        "char_id": action.partner_move.char_id,
                        "strategy": action.partner_move.strategy,
                        "move_id": action.partner_move.move_id,
                    }
                )

        await self.combat_manager.transfer_intents_to_actions(session_id, actions_json, deletes)

    # ==========================================================================
    # 2. МЕТОДЫ ДЛЯ ИСПОЛНИТЕЛЯ (HEAVYWEIGHT)
    # ==========================================================================

    async def load_battle_context(self, session_id: str) -> BattleContext | None:
        """
        Полная пакетная загрузка контекста и всей очереди задач.
        Использует CombatSessionManager.load_full_context_data.
        """
        # 1. Meta
        meta_raw = await self.combat_manager.get_rbc_session_meta(session_id)
        if not meta_raw:
            return None
        meta = self._parse_meta(meta_raw)

        # 2. Actors List
        all_actor_ids: list[int | str] = []
        for team_ids in meta.teams.values():
            all_actor_ids.extend(team_ids)

        # 3. Full Load via Manager
        structured_data = await self.combat_manager.load_full_context_data(session_id, all_actor_ids)

        actors_map = {}
        moves_cache = {}

        # Pre-calculate team mapping for O(1) lookup
        id_to_team_map = {
            str(actor_id): team_name for team_name, actor_ids in meta.teams.items() for actor_id in actor_ids
        }

        for cid, data in structured_data.items():
            if cid == "global_queue":
                continue

            if not data.get("meta"):
                continue

            # Build Snapshot
            actors_map[cid] = self._build_snapshot(
                cid,
                id_to_team_map.get(str(cid), "neutral"),
                data["state"],
                data["raw"],
                data["loadout"],
                data["meta"],
                data["statuses"],
                data["xp"],
                data.get("skills", {}),
            )

            # Cache Move
            if data.get("move"):
                moves_cache[cid] = data["move"]

        return BattleContext(
            session_id=session_id, meta=meta, actors=actors_map, moves_cache=moves_cache, pending_logs=[]
        )

    async def load_snapshot_context(self, session_id: str) -> BattleContext | None:
        """
        Легкая загрузка для UI (без XP и Queue).
        """
        return await self.load_battle_context(session_id)

    async def commit_session(self, ctx: BattleContext, processed_action_ids: list[str]) -> None:
        """
        Атомарное сохранение изменений актёров, логов и возврат целей.
        ВСЕ операции выполняются в ОДНОЙ транзакции Redis.
        """
        updates = {}

        # 1. Prepare Updates (Actors State)
        for cid, actor in ctx.actors.items():
            actor_updates = {
                "state": {
                    "hp": actor.meta.hp,
                    "max_hp": actor.meta.max_hp,
                    "en": actor.meta.en,
                    "max_en": actor.meta.max_en,
                    "tactics": actor.meta.tactics,
                    "is_dead": actor.meta.is_dead,
                    "tokens": actor.meta.tokens,
                },
                "statuses": actor.statuses.model_dump(),
                "xp": actor.xp_buffer,
                "raw": actor.raw.model_dump(),
            }
            updates[cid] = actor_updates

        # 2. Prepare Logs
        logs = [json.dumps(entry) for entry in ctx.pending_logs]

        # 3. Update dead_actors list if needed
        dead_actors_update = None
        if ctx.pending_dead_actors:
            # Merge with existing dead_actors
            updated_dead = list(set(ctx.meta.dead_actors + ctx.pending_dead_actors))
            dead_actors_update = json.dumps(updated_dead)

        # 4. АТОМАРНЫЙ Commit (state + logs + actions + targets + dead_actors)
        await self.combat_manager.commit_battle_results(
            ctx.session_id,
            updates,
            logs,
            len(processed_action_ids),
            target_returns=ctx.pending_target_returns,
            dead_actors=dead_actors_update,
        )

    # ==========================================================================
    # 3. HELPERS
    # ==========================================================================

    def _parse_meta(self, raw: dict) -> BattleMeta:
        """
        Парсит мета-данные из Redis Hash (dict[str, str]).
        """

        def d(k):
            return raw.get(k)

        return BattleMeta(
            active=int(d("active") or 1),
            step_counter=int(d("step_counter") or 0),
            active_actors_count=0,
            teams=json.loads(d("teams") or "{}"),
            actors_info=json.loads(d("actors_info") or "{}"),
            dead_actors=json.loads(d("dead_actors") or "[]"),
            last_activity_at=int(d("last_activity_at") or 0),
            battle_type=d("battle_type") or "standard",
            location_id=d("location_id") or "unknown",
        )

    def _build_snapshot(
        self, cid, team, r_state, r_raw, r_loadout, r_meta, r_statuses, r_xp, r_skills
    ) -> ActorSnapshot:
        meta_dict = r_meta or {}

        meta = ActorMetaDTO(
            id=cid,
            name=meta_dict.get("name", "Unknown"),
            type=meta_dict.get("type", "unknown"),
            team=team,
            template_id=meta_dict.get("template_id"),
            is_ai=meta_dict.get("is_ai", False),
            # State fields (from r_state dict)
            hp=int(r_state.get("hp", 0)),
            max_hp=int(r_state.get("max_hp", 0)),
            en=int(r_state.get("en", 0)),
            max_en=int(r_state.get("max_en", 0)),
            tactics=int(r_state.get("tactics", 0)),
            is_dead=bool(r_state.get("is_dead", False)),
            tokens=r_state.get("tokens") or {},
        )

        raw_dict = r_raw or {}
        loadout_dict = r_loadout or {}

        merged_raw = {
            "attributes": raw_dict.get("attributes", {}),
            "modifiers": raw_dict.get("modifiers", {}),
        }

        loadout = ActorLoadoutDTO(
            layout=loadout_dict.get("equipment_layout", {}),
            belt=loadout_dict.get("belt", []),
            known_abilities=loadout_dict.get("known_abilities", []),
            tags=loadout_dict.get("tags", []),
        )

        statuses_dict = r_statuses or {"abilities": [], "effects": []}
        statuses = ActorStatusesDTO(
            abilities=[ActiveAbilityDTO(**a) for a in statuses_dict.get("abilities", [])],
            effects=[ActiveEffectDTO(**e) for e in statuses_dict.get("effects", [])],
        )

        return ActorSnapshot(
            meta=meta,
            raw=ActorRawDTO(**merged_raw),
            loadout=loadout,
            statuses=statuses,
            xp_buffer=r_xp or {},
            skills=r_skills or {},
        )


CombatDataService = CombatSessionIntegration
