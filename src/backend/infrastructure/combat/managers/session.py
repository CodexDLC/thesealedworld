from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from codex_platform.redis_service import RedisService

    from src.backend.features.combat.dto.ids import ActorId
    from src.backend.features.combat.dto.session import SessionDataDTO, TargetReturnDTO


class CombatSessionManager:
    """Combat-owned Redis access for RBC-compatible combat sessions."""

    DEFAULT_TTL_SECONDS = 3600
    HISTORY_TTL_SECONDS = 86400

    def __init__(self, redis: RedisService) -> None:
        self.redis = redis

    @staticmethod
    def meta_key(session_id: str) -> str:
        return f"combat:rbc:{session_id}:meta"

    @staticmethod
    def actor_key(session_id: str, actor_id: str | int) -> str:
        return f"combat:rbc:{session_id}:actor:{actor_id}"

    @staticmethod
    def targets_key(session_id: str) -> str:
        return f"combat:rbc:{session_id}:targets"

    @staticmethod
    def moves_key(session_id: str, actor_id: str | int) -> str:
        return f"combat:rbc:{session_id}:actor:{actor_id}:moves"

    @staticmethod
    def action_queue_key(session_id: str) -> str:
        return f"combat:rbc:{session_id}:q:actions"

    @staticmethod
    def queue_key(session_id: str) -> str:
        return CombatSessionManager.action_queue_key(session_id)

    @staticmethod
    def log_key(session_id: str) -> str:
        return f"combat:rbc:{session_id}:logs"

    @staticmethod
    def analytics_key(session_id: str) -> str:
        return f"combat:rbc:{session_id}:analytics"

    @staticmethod
    def finalization_key(session_id: str) -> str:
        return f"combat:finalize:{session_id}"

    @staticmethod
    def character_finalization_key(char_id: str | int) -> str:
        return f"combat:finalize:char:{char_id}:latest"

    @staticmethod
    def busy_lock_key(session_id: str) -> str:
        return f"combat:rbc:{session_id}:sys:busy"

    def _client(self) -> Any:
        if hasattr(self.redis, "redis_client"):
            return self.redis.redis_client
        return self.redis.pipeline.client

    def _json(self) -> Any:
        if hasattr(self.redis, "json_module"):
            return self.redis.json_module
        return self._client().json()

    async def create_session_batch(
        self,
        session_id: str,
        data: SessionDataDTO,
        *,
        ttl: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        client = self._client()
        async with client.pipeline(transaction=False) as pipe:
            pipe.hset(self.meta_key(session_id), mapping={k: self._redis_value(v) for k, v in data.meta.items()})
            pipe.expire(self.meta_key(session_id), ttl)

            pipe.json().set(self.targets_key(session_id), "$", data.targets)
            pipe.expire(self.targets_key(session_id), ttl)

            for actor_id, actor_data in data.actors.items():
                actor_key = self.actor_key(session_id, actor_id)
                pipe.json().set(actor_key, "$", actor_data)
                pipe.expire(actor_key, ttl)

                moves_key = self.moves_key(session_id, actor_id)
                pipe.json().set(moves_key, "$", {"exchange": {}, "item": {}, "instant": {}, "system": {}})
                pipe.expire(moves_key, ttl)

            pipe.delete(self.action_queue_key(session_id))
            pipe.delete(self.log_key(session_id))
            pipe.delete(self.analytics_key(session_id))
            await pipe.execute()
        logger.bind(session_id=session_id, actor_count=len(data.actors)).info("CombatSessionCreated")

    async def universal_hot_join(
        self,
        session_id: str,
        actor_id: int | str,
        team_name: str,
        actor_data: dict[str, Any],
        is_ai: bool = True,
    ) -> None:
        async with self._client().pipeline(transaction=False) as pipe:
            actor_key = self.actor_key(session_id, actor_id)
            pipe.json().set(actor_key, "$", actor_data)
            pipe.expire(actor_key, self.DEFAULT_TTL_SECONDS)
            moves_key = self.moves_key(session_id, actor_id)
            pipe.json().set(moves_key, "$", {"exchange": {}, "item": {}, "instant": {}})
            pipe.expire(moves_key, self.DEFAULT_TTL_SECONDS)
            await pipe.execute()

        script = """
        local meta_key = KEYS[1]
        local targets_key = KEYS[2]
        local char_id = ARGV[1]
        local team_name = ARGV[2]
        local is_ai = ARGV[3]

        local info_raw = redis.call("HGET", meta_key, "actors_info")
        local info = cjson.decode(info_raw or "{}")
        info[char_id] = (is_ai == "1") and "ai" or "player"
        redis.call("HSET", meta_key, "actors_info", cjson.encode(info))

        local teams_raw = redis.call("HGET", meta_key, "teams")
        local teams = cjson.decode(teams_raw or "{}")
        if not teams[team_name] then teams[team_name] = {} end

        local exists = false
        for _, id in ipairs(teams[team_name]) do
            if tostring(id) == char_id then exists = true break end
        end
        if not exists then
            table.insert(teams[team_name], tonumber(char_id) or char_id)
            redis.call("HSET", meta_key, "teams", cjson.encode(teams))
        end

        local targets_raw = redis.call("JSON.GET", targets_key, "$")
        local all_targets = {}
        if targets_raw then
            all_targets = cjson.decode(targets_raw)[1] or {}
        end

        local new_actor_targets = {}

        for actor, target_list in pairs(all_targets) do
            local is_enemy = true
            if teams[team_name] then
                for _, member_id in ipairs(teams[team_name]) do
                    if tostring(member_id) == actor then
                        is_enemy = false
                        break
                    end
                end
            end

            if is_enemy then
                local already_target = false
                for _, target_id in ipairs(target_list) do
                    if tostring(target_id) == char_id then already_target = true break end
                end
                if not already_target then
                    table.insert(target_list, tonumber(char_id) or char_id)
                end
                table.insert(new_actor_targets, tonumber(actor) or actor)
            end
        end

        all_targets[char_id] = new_actor_targets
        redis.call("JSON.SET", targets_key, "$", cjson.encode(all_targets))
        return 1
        """
        await self._client().eval(
            script,
            2,
            self.meta_key(session_id),
            self.targets_key(session_id),
            str(actor_id),
            team_name,
            "1" if is_ai else "0",
        )
        logger.bind(session_id=session_id, actor_id=actor_id).info("CombatActorHotJoined")

    async def get_meta(self, session_id: str) -> dict[str, Any] | None:
        raw = await self._client().hgetall(self.meta_key(session_id))
        if not raw:
            return None
        return {self._decode(k): self._decode(v) for k, v in raw.items()}

    async def scan_active_sessions(self) -> list[tuple[str, dict[str, Any]]]:
        """Scan Redis for all active combat sessions. Returns list of (session_id, meta)."""
        client = self._client()
        session_ids: list[str] = []
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor, match="combat:rbc:*:meta", count=100)
            for key in keys:
                parts = self._decode(key).split(":")
                if len(parts) == 4:
                    session_ids.append(parts[2])
            if cursor == 0:
                break
        result = []
        for sid in session_ids:
            meta = await self.get_meta(sid)
            if meta and str(meta.get("active", "0")) == "1":
                result.append((sid, meta))
        return result

    async def get_rbc_session_meta(self, session_id: str) -> dict[str, Any] | None:
        return await self.get_meta(session_id)

    async def set_winner(self, session_id: str, winner: str) -> None:
        await self._client().hset(
            self.meta_key(session_id),
            mapping={"active": 0, "winner": winner, "status": "finished", "updated_at": int(time.time())},
        )

    async def touch_activity(self, session_id: str) -> None:
        await self._client().hset(self.meta_key(session_id), "last_activity_at", int(time.time()))
        await self.refresh_session_ttl(session_id)

    async def claim_initial_ai_seed(self, session_id: str) -> bool:
        return bool(await self._client().hsetnx(self.meta_key(session_id), "initial_ai_seeded_at", int(time.time())))

    async def mark_started(self, session_id: str) -> bool:
        return bool(await self._client().hsetnx(self.meta_key(session_id), "started_at", int(time.time())))

    async def refresh_session_ttl(self, session_id: str, *, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        meta = await self.get_meta(session_id)
        actor_ids = self.actor_ids_from_meta(meta or {})
        async with self._client().pipeline(transaction=False) as pipe:
            pipe.expire(self.meta_key(session_id), ttl)
            pipe.expire(self.targets_key(session_id), ttl)
            pipe.expire(self.action_queue_key(session_id), ttl)
            pipe.expire(self.log_key(session_id), ttl)
            pipe.expire(self.analytics_key(session_id), ttl)
            for actor_id in actor_ids:
                pipe.expire(self.actor_key(session_id, actor_id), ttl)
                pipe.expire(self.moves_key(session_id, actor_id), ttl)
            await pipe.execute()

    async def get_actor(self, session_id: str, actor_id: str | int) -> dict[str, Any] | None:
        result = await self._json().get(self.actor_key(session_id, actor_id), "$")
        return self._first_dict(result)

    async def get_actor_state(self, session_id: str, actor_id: str | int) -> dict[str, Any] | None:
        result = await self._json().get(self.actor_key(session_id, actor_id), "$.meta")
        meta = self._first_dict(result)
        if not meta:
            return None
        return {
            "hp": meta.get("hp"),
            "max_hp": meta.get("max_hp"),
            "en": meta.get("en"),
            "max_en": meta.get("max_en"),
            "stamina": meta.get("stamina"),
            "max_stamina": meta.get("max_stamina"),
            "tactics": meta.get("tactics"),
            "is_dead": meta.get("is_dead"),
            "tokens": meta.get("tokens"),
            "token_progress": meta.get("token_progress"),
            "afk_level": meta.get("afk_level"),
            "exchange_counter": meta.get("exchange_counter"),
            "feints": meta.get("feints"),
        }

    async def get_actor_raw(self, session_id: str, actor_id: str | int) -> dict[str, Any] | None:
        result = await self._json().get(self.actor_key(session_id, actor_id), "$.raw")
        return self._first_dict(result)

    async def get_actors_batch(
        self,
        session_id: str,
        actor_ids: Sequence[str | int],
    ) -> dict[str, dict[str, Any] | None]:
        if not actor_ids:
            return {}
        client = self._client()
        async with client.pipeline(transaction=False) as pipe:
            for actor_id in actor_ids:
                pipe.json().get(self.actor_key(session_id, actor_id), "$")
            results = await pipe.execute(raise_on_error=False)
        return {
            str(actor_id): None if isinstance(result, Exception) else self._first_dict(result)
            for actor_id, result in zip(actor_ids, results, strict=False)
        }

    async def get_targets(self, session_id: str) -> dict[str, list[Any]]:
        result = await self._json().get(self.targets_key(session_id), "$")
        value = self._first(result)
        return value if isinstance(value, dict) else {}

    async def pop_player_target(self, session_id: str, actor_id: str | int) -> ActorId | None:
        result = await self._json().arrpop(self.targets_key(session_id), self._json_member_path(actor_id), 0)
        value = self._first(result)
        return str(value) if value is not None else None

    async def peek_player_target(self, session_id: str, actor_id: str | int) -> ActorId | None:
        result = await self._json().get(self.targets_key(session_id), f"{self._json_member_path(actor_id)}[0]")
        value = self._first(result)
        return str(value) if value is not None else None

    async def load_snapshot_data_batch(
        self,
        session_id: str,
        actor_ids: Sequence[str | int],
    ) -> tuple[dict[str, list[Any]], list[Any]]:
        async with self._client().pipeline(transaction=False) as pipe:
            pipe.json().get(self.targets_key(session_id), "$")
            for actor_id in actor_ids:
                actor_key = self.actor_key(session_id, actor_id)
                pipe.json().get(actor_key, "$.meta", "$.loadout", "$.statuses")
                pipe.json().get(self.moves_key(session_id, actor_id), "$")
            results = await pipe.execute(raise_on_error=False)

        targets = self._first(results[0]) if results else {}
        targets_map = targets if isinstance(targets, dict) else {}
        actors: list[Any] = []
        raw_actor_results = results[1:]
        for index in range(0, len(raw_actor_results), 2):
            actor_partial = raw_actor_results[index]
            moves = raw_actor_results[index + 1] if index + 1 < len(raw_actor_results) else {}
            if isinstance(actor_partial, Exception) or not actor_partial:
                actors.append(None)
                continue
            actors.append(
                {
                    "meta": self._first(actor_partial.get("$.meta", [{}])),
                    "loadout": self._first(actor_partial.get("$.loadout", [{}])),
                    "statuses": self._first(actor_partial.get("$.statuses", [{"abilities": [], "effects": []}])),
                    "moves": self._first(moves) if not isinstance(moves, Exception) else {},
                }
            )
        return targets_map, actors

    async def get_moves(self, session_id: str, actor_id: str | int) -> dict[str, Any]:
        result = await self._json().get(self.moves_key(session_id, actor_id), "$")
        value = self._first(result)
        return value if isinstance(value, dict) else {}

    async def get_moves_batch(self, session_id: str, actor_ids: Sequence[str | int]) -> dict[str, Any]:
        if not actor_ids:
            return {}
        async with self._client().pipeline(transaction=False) as pipe:
            for actor_id in actor_ids:
                pipe.json().get(self.moves_key(session_id, actor_id), "$")
            results = await pipe.execute(raise_on_error=False)
        return {
            str(actor_id): self._first(result)
            for actor_id, result in zip(actor_ids, results, strict=False)
            if result and not isinstance(result, Exception)
        }

    async def check_move_exists(self, session_id: str, actor_id: str | int) -> bool:
        return bool(await self._client().exists(self.moves_key(session_id, actor_id)))

    async def append_move(self, session_id: str, actor_id: str | int, strategy: str, move_dto: dict[str, Any]) -> None:
        move_id = move_dto.get("move_id")
        if not move_id:
            raise ValueError("Move DTO must have move_id")
        key = self.moves_key(session_id, actor_id)
        await self._json().set(key, f"$.{strategy}.{move_id}", move_dto)
        await self._client().expire(key, self.DEFAULT_TTL_SECONDS)

    async def append_moves_batch(self, session_id: str, actor_id: str | int, moves: list[Any]) -> None:
        if not moves:
            return
        key = self.moves_key(session_id, actor_id)
        async with self._client().pipeline(transaction=False) as pipe:
            for move in moves:
                data = move.model_dump(mode="json") if hasattr(move, "model_dump") else dict(move)
                pipe.json().set(key, f"$.{data['strategy']}.{data['move_id']}", data)
            pipe.expire(key, self.DEFAULT_TTL_SECONDS)
            await pipe.execute()

    async def register_exchange_move_atomic(
        self,
        session_id: str,
        actor_id: str | int,
        target_id: str | int,
        move_dto: dict[str, Any],
    ) -> bool:
        move_id = move_dto.get("move_id")
        if not move_id:
            return False
        script = """
        local actor_path = '$["' .. ARGV[1] .. '"]'
        local idx = redis.call('JSON.ARRINDEX', KEYS[1], actor_path, cjson.encode(ARGV[2]))
        if (not idx or idx[1] == -1) and tonumber(ARGV[2]) then
            idx = redis.call('JSON.ARRINDEX', KEYS[1], actor_path, tonumber(ARGV[2]))
        end
        if not idx or idx[1] == -1 then return 0 end
        redis.call('JSON.ARRPOP', KEYS[1], actor_path, idx[1])
        redis.call('JSON.SET', KEYS[2], '$.exchange.' .. ARGV[4], ARGV[3])
        redis.call('EXPIRE', KEYS[2], ARGV[5])
        return 1
        """
        result = await self._client().eval(
            script,
            2,
            self.targets_key(session_id),
            self.moves_key(session_id, actor_id),
            str(actor_id),
            str(target_id),
            json.dumps(move_dto),
            str(move_id),
            str(self.DEFAULT_TTL_SECONDS),
        )
        return bool(result)

    async def register_moves_batch_atomic(
        self,
        session_id: str,
        actor_id: str | int,
        moves_data: list[dict[str, Any]],
    ) -> list[str]:
        if not moves_data:
            return []
        script = """
        local success = 0
        local accepted = {}
        local moves = cjson.decode(ARGV[2])
        local actor_path = '$["' .. ARGV[1] .. '"]'
        for _, item in ipairs(moves) do
            local idx = redis.call('JSON.ARRINDEX', KEYS[1], actor_path, cjson.encode(tostring(item.target_id)))
            if (not idx or idx[1] == -1) and tonumber(item.target_id) then
                idx = redis.call('JSON.ARRINDEX', KEYS[1], actor_path, tonumber(item.target_id))
            end
            if idx and idx[1] ~= -1 then
                redis.call('JSON.ARRPOP', KEYS[1], actor_path, idx[1])
                redis.call('JSON.SET', KEYS[2], '$.' .. item.strategy .. '.' .. item.move_id, item.move_json)
                success = success + 1
                table.insert(accepted, item.move_id)
            end
        end
        redis.call('EXPIRE', KEYS[2], ARGV[3])
        return cjson.encode(accepted)
        """
        result = await self._client().eval(
            script,
            2,
            self.targets_key(session_id),
            self.moves_key(session_id, actor_id),
            str(actor_id),
            json.dumps(moves_data),
            str(self.DEFAULT_TTL_SECONDS),
        )
        accepted = json.loads(result) if result else []
        return [str(move_id) for move_id in accepted] if isinstance(accepted, list) else []

    async def get_queue_size(self, session_id: str) -> int:
        return int(await self._client().llen(self.action_queue_key(session_id)))

    async def load_actions_batch(self, session_id: str, batch_size: int) -> list[str]:
        return list(await self._client().lrange(self.action_queue_key(session_id), 0, max(0, batch_size - 1)))

    async def transfer_intents_to_actions(
        self,
        session_id: str,
        actions_json: list[str],
        deletes: list[dict[str, Any]],
    ) -> None:
        if not actions_json and not deletes:
            return
        script = """
        local actions = cjson.decode(ARGV[1])
        local fallback_deletes = cjson.decode(ARGV[2])
        local ttl = tonumber(ARGV[3])
        local queue_key = KEYS[1]
        local session_id = ARGV[4]
        local pushed = 0

        local function moves_key(actor_id)
            return 'combat:rbc:' .. session_id .. ':actor:' .. tostring(actor_id) .. ':moves'
        end

        local function move_path(move)
            return '$.' .. tostring(move.strategy) .. '.' .. tostring(move.move_id)
        end

        local function move_exists(move)
            local raw = redis.call('JSON.GET', moves_key(move.char_id), move_path(move))
            return raw and raw ~= '[]' and raw ~= 'null'
        end

        local function delete_move(move)
            local key = moves_key(move.char_id)
            redis.call('JSON.DEL', key, move_path(move))
            redis.call('EXPIRE', key, ttl)
        end

        for _, action_json in ipairs(actions) do
            local action = cjson.decode(action_json)
            local valid = action.move and move_exists(action.move)
            local partner_move = action.partner_move

            if valid and partner_move ~= nil and partner_move ~= cjson.null then
                valid = move_exists(partner_move)
            end

            if valid then
                redis.call('RPUSH', queue_key, action_json)
                delete_move(action.move)
                if partner_move ~= nil and partner_move ~= cjson.null then
                    delete_move(partner_move)
                end
                pushed = pushed + 1
            end
        end

        if #actions == 0 then
            for _, item in ipairs(fallback_deletes) do
                local key = moves_key(item.char_id)
                redis.call('JSON.DEL', key, '$.' .. tostring(item.strategy) .. '.' .. tostring(item.move_id))
                redis.call('EXPIRE', key, ttl)
            end
        end

        return pushed
        """
        await self._client().eval(
            script,
            1,
            self.action_queue_key(session_id),
            json.dumps(actions_json),
            json.dumps(deletes),
            str(self.DEFAULT_TTL_SECONDS),
            session_id,
        )

    async def push_actions_batch(self, session_id: str, actions_json: list[str]) -> None:
        if actions_json:
            await self._client().rpush(self.action_queue_key(session_id), *actions_json)

    async def load_full_context_data(self, session_id: str, actor_ids: Sequence[str | int]) -> dict[str, Any]:
        async with self._client().pipeline(transaction=False) as pipe:
            for actor_id in actor_ids:
                pipe.json().get(self.actor_key(session_id, actor_id), "$")
                pipe.json().get(self.moves_key(session_id, actor_id), "$")
            pipe.lrange(self.action_queue_key(session_id), 0, -1)
            results = await pipe.execute(raise_on_error=False)

        data: dict[str, Any] = {}
        for index, actor_id in enumerate(actor_ids):
            actor_data = self._first_dict(results[index * 2]) if index * 2 < len(results) else {}
            moves_data = self._first(results[index * 2 + 1]) if index * 2 + 1 < len(results) else {}
            actor_data = actor_data or {}
            meta = actor_data.get("meta", {})
            data[str(actor_id)] = {
                "state": {
                    "hp": meta.get("hp", 0),
                    "max_hp": meta.get("max_hp", 0),
                    "en": meta.get("en", 0),
                    "max_en": meta.get("max_en", 0),
                    "stamina": meta.get("stamina", 0),
                    "max_stamina": meta.get("max_stamina", 0),
                    "tactics": meta.get("tactics", 0),
                    "afk_level": meta.get("afk_level", 0),
                    "exchange_counter": meta.get("exchange_counter", 0),
                    "is_dead": meta.get("is_dead", False),
                    "tokens": meta.get("tokens", {}),
                    "token_progress": meta.get("token_progress", {}),
                    "feints": meta.get("feints", {}),
                },
                "raw": actor_data.get("raw", {}),
                "loadout": actor_data.get("loadout", {}),
                "meta": meta,
                "statuses": actor_data.get("statuses", {"abilities": [], "effects": []}),
                "xp": actor_data.get("xp_buffer", {}),
                "skills": actor_data.get("skills", {}),
                "stats": actor_data.get("stats"),
                "explanation": actor_data.get("explanation", {}),
                "move": moves_data or {},
            }
        data["global_queue"] = results[-1] if results else []
        return data

    async def commit_battle_results(
        self,
        session_id: str,
        updates: dict[str, Any],
        logs: list[dict[str, Any] | str],
        processed_count: int,
        target_returns: Sequence[TargetReturnDTO] | None = None,
        dead_actors: str | None = None,
        dead_actor_ids: Iterable[Any] | None = None,
        meta_update: dict[str, Any] | None = None,
        analytics: list[dict[str, Any] | str] | None = None,
    ) -> None:
        grouped_logs = await self._merge_logs_by_turn(session_id, logs) if logs else {}
        analytics_entries = self._analytics_mapping(analytics or [])
        async with self._client().pipeline(transaction=False) as pipe:
            for actor_id, actor_update in updates.items():
                key = self.actor_key(session_id, actor_id)
                if "state" in actor_update:
                    state_update = actor_update["state"]
                    pipe.json().merge(key, "$.meta", state_update)
                    if "feints" in state_update:
                        pipe.json().set(key, "$.meta.feints", state_update["feints"])
                if "statuses" in actor_update:
                    pipe.json().set(key, "$.statuses", actor_update["statuses"])
                if "xp" in actor_update:
                    pipe.json().set(key, "$.xp_buffer", actor_update["xp"])
                if "raw" in actor_update:
                    pipe.json().set(key, "$.raw", actor_update["raw"])
                if "raw_temp" in actor_update:
                    pipe.json().set(key, "$.raw.temp", actor_update["raw_temp"])
                if "stats" in actor_update:
                    pipe.json().set(key, "$.stats", actor_update["stats"])
                if "explanation" in actor_update:
                    pipe.json().set(key, "$.explanation", actor_update["explanation"])
            if grouped_logs:
                pipe.hset(self.log_key(session_id), mapping=grouped_logs)
            if analytics_entries:
                pipe.hset(self.analytics_key(session_id), mapping=analytics_entries)
            if processed_count > 0:
                pipe.ltrim(self.action_queue_key(session_id), processed_count, -1)
            if dead_actor_ids:
                pipe.eval(
                    self._prune_dead_targets_script(),
                    1,
                    self.targets_key(session_id),
                    json.dumps([str(actor_id) for actor_id in dead_actor_ids]),
                )
            if target_returns:
                for pair in target_returns:
                    pipe.json().arrappend(
                        self.targets_key(session_id), self._json_member_path(pair["source_id"]), pair["target_id"]
                    )
            if dead_actors is not None:
                pipe.hset(self.meta_key(session_id), "dead_actors", dead_actors)
            if meta_update:
                pipe.hset(self.meta_key(session_id), mapping={k: self._redis_value(v) for k, v in meta_update.items()})
            await pipe.execute()
        await self.refresh_session_ttl(session_id)

    @staticmethod
    def _prune_dead_targets_script() -> str:
        return """
        local raw = redis.call('JSON.GET', KEYS[1], '$')
        if not raw then return 0 end

        local decoded = cjson.decode(raw)
        local targets = decoded[1] or {}
        local dead = cjson.decode(ARGV[1])
        local dead_set = {}
        for _, actor_id in ipairs(dead) do
            dead_set[tostring(actor_id)] = true
        end

        local function member_path(actor_id)
            local escaped = tostring(actor_id):gsub('\\\\', '\\\\\\\\'):gsub('"', '\\\\"')
            return '$["' .. escaped .. '"]'
        end

        local function set_queue(actor_id, queue)
            local path = member_path(actor_id)
            redis.call('JSON.SET', KEYS[1], path, '[]')
            for _, target_id in ipairs(queue) do
                redis.call('JSON.ARRAPPEND', KEYS[1], path, cjson.encode(target_id))
            end
        end

        for actor_id, queue in pairs(targets) do
            if dead_set[tostring(actor_id)] then
                set_queue(actor_id, {})
            else
                local pruned = {}
                if type(queue) == 'table' then
                    for _, target_id in ipairs(queue) do
                        if not dead_set[tostring(target_id)] then
                            table.insert(pruned, target_id)
                        end
                    end
                end
                set_queue(actor_id, pruned)
            end
        end

        return 1
        """

    async def consume_feint_atomic(self, session_id: str, actor_id: str | int, feint_id: str) -> dict[str, int] | None:
        script = """
        local raw = redis.call('JSON.GET', KEYS[1], '$.meta.feints.hand')
        if not raw then return nil end
        local hand = cjson.decode(raw)[1]
        if not hand or not hand[ARGV[1]] then return nil end
        local cost = hand[ARGV[1]]
        redis.call('JSON.DEL', KEYS[1], '$.meta.feints.hand.' .. ARGV[1])
        local pinned_raw = redis.call('JSON.GET', KEYS[1], '$.meta.feints.pinned')
        if pinned_raw then
            local pinned = cjson.decode(pinned_raw)[1]
            if pinned == ARGV[1] then
                redis.call('JSON.SET', KEYS[1], '$.meta.feints.pinned', 'null')
            end
        end
        return cjson.encode(cost)
        """
        result = await self._client().eval(script, 1, self.actor_key(session_id, actor_id), feint_id)
        return json.loads(result) if result else None

    async def return_feint_to_hand(
        self,
        session_id: str,
        actor_id: str | int,
        feint_id: str,
        cost: dict[str, int],
    ) -> None:
        await self._json().set(self.actor_key(session_id, actor_id), f"$.meta.feints.hand.{feint_id}", cost)

    async def pin_feint_atomic(self, session_id: str, actor_id: str | int, feint_id: str | None) -> bool:
        if feint_id is None:
            await self._json().set(self.actor_key(session_id, actor_id), "$.meta.feints.pinned", None)
            return True

        script = """
        local raw = redis.call('JSON.GET', KEYS[1], '$.meta.feints.hand')
        if not raw then return 0 end
        local hand = cjson.decode(raw)[1]
        if not hand or not hand[ARGV[1]] then return 0 end
        redis.call('JSON.SET', KEYS[1], '$.meta.feints.pinned', cjson.encode(ARGV[1]))
        return 1
        """
        result = await self._client().eval(script, 1, self.actor_key(session_id, actor_id), feint_id)
        return bool(result)

    async def append_log(self, session_id: str, entry: dict[str, Any] | str) -> None:
        grouped = await self._merge_logs_by_turn(session_id, [entry])
        await self._client().hset(self.log_key(session_id), mapping=grouped)

    async def append_analytics(self, session_id: str, entry: dict[str, Any] | str) -> None:
        mapping = self._analytics_mapping([entry])
        if mapping:
            await self._client().hset(self.analytics_key(session_id), mapping=mapping)

    async def get_analytics(self, session_id: str) -> dict[str, Any]:
        raw = dict(await self._client().hgetall(self.analytics_key(session_id)))
        analytics: dict[str, Any] = {}
        for key, payload in raw.items():
            key = self._decode(key)
            payload = self._decode(payload)
            try:
                analytics[str(key)] = json.loads(payload)
            except (TypeError, json.JSONDecodeError):
                analytics[str(key)] = payload
        return dict(sorted(analytics.items(), key=lambda item: self._turn_sort_key(item[0].split(":", 1)[0])))

    async def save_finalization(
        self,
        session_id: str,
        payload: dict[str, Any],
        *,
        char_ids: Sequence[int | str],
        ttl: int = HISTORY_TTL_SECONDS,
    ) -> None:
        encoded = json.dumps(payload)
        async with self._client().pipeline(transaction=False) as pipe:
            pipe.set(self.finalization_key(session_id), encoded, ex=ttl)
            for char_id in char_ids:
                pipe.set(self.character_finalization_key(char_id), session_id, ex=ttl)
            await pipe.execute()

    async def get_finalization(self, session_id: str) -> dict[str, Any] | None:
        raw = await self._client().get(self.finalization_key(session_id))
        if not raw:
            return None
        raw = self._decode(raw)
        try:
            decoded = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
        return decoded if isinstance(decoded, dict) else None

    async def get_latest_finalization_id_for_character(self, char_id: int | str) -> str | None:
        value = await self._client().get(self.character_finalization_key(char_id))
        if not value:
            return None
        return self._decode(value)

    async def clear_latest_finalization_id_for_character(self, char_id: int | str) -> None:
        await self._client().delete(self.character_finalization_key(char_id))

    async def add_log(self, session_id: str, text: str, tags: list[str] | None = None) -> None:
        await self.append_log(session_id, {"text": text, "timestamp": time.time(), "tags": tags or []})

    async def get_logs(self, session_id: str, *, start: int = 0, stop: int = -1) -> list[str]:
        logs = self._flatten_logs_by_turn(await self.get_logs_by_turn(session_id))
        return self._slice_logs(logs, start=start, stop=stop)

    async def get_logs_by_turn(self, session_id: str) -> dict[str, list[str]]:
        raw = dict(await self._client().hgetall(self.log_key(session_id)))
        grouped: dict[str, list[str]] = {}
        for turn, payload in raw.items():
            if isinstance(turn, bytes):
                turn = turn.decode()
            if isinstance(payload, bytes):
                payload = payload.decode()
            try:
                values = json.loads(payload)
            except (TypeError, json.JSONDecodeError):
                values = [str(payload)]
            grouped[str(turn)] = [value if isinstance(value, str) else json.dumps(value) for value in values]
        return dict(sorted(grouped.items(), key=lambda item: self._turn_sort_key(item[0])))

    async def get_combat_log_list(self, session_id: str) -> list[str]:
        return await self.get_logs(session_id, start=0, stop=-1)

    async def count_logs(self, session_id: str) -> int:
        return len(self._flatten_logs_by_turn(await self.get_logs_by_turn(session_id)))

    async def _merge_logs_by_turn(self, session_id: str, logs: list[dict[str, Any] | str]) -> dict[str, str]:
        existing = await self.get_logs_by_turn(session_id)
        for turn, payload in self._group_logs_by_turn(logs).items():
            existing.setdefault(turn, []).extend(json.loads(payload))
        return {turn: json.dumps(values) for turn, values in existing.items()}

    @classmethod
    def _group_logs_by_turn(cls, logs: list[dict[str, Any] | str]) -> dict[str, str]:
        grouped: dict[str, list[str]] = {}
        for entry in logs:
            payload = entry if isinstance(entry, str) else json.dumps(entry)
            turn = cls._log_turn(payload, entry)
            grouped.setdefault(turn, []).append(payload)
        return {turn: json.dumps(values) for turn, values in grouped.items()}

    @staticmethod
    def _analytics_mapping(analytics: list[dict[str, Any] | str]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for index, entry in enumerate(analytics):
            payload = entry if isinstance(entry, str) else json.dumps(entry)
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                decoded = {}
            if isinstance(decoded, dict) and decoded.get("k") == "profile":
                mapping["_profile"] = payload
                continue
            turn = decoded.get("t", 0) if isinstance(decoded, dict) else 0
            seq = decoded.get("seq", index) if isinstance(decoded, dict) else index
            mapping[f"{turn}:{seq}"] = payload
        return mapping

    @staticmethod
    def _log_turn(payload: str, entry: dict[str, Any] | str) -> str:
        if isinstance(entry, dict):
            return str(entry.get("global_turn", 0))
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return "0"
        if isinstance(decoded, dict):
            return str(decoded.get("global_turn", 0))
        return "0"

    @classmethod
    def _flatten_logs_by_turn(cls, logs_by_turn: dict[str, list[str]]) -> list[str]:
        flat: list[str] = []
        for turn in sorted(logs_by_turn, key=cls._turn_sort_key):
            flat.extend(logs_by_turn[turn])
        return flat

    @staticmethod
    def _slice_logs(logs: list[str], *, start: int = 0, stop: int = -1) -> list[str]:
        end = None if stop == -1 else stop + 1
        return logs[start:end]

    @staticmethod
    def _turn_sort_key(turn: str) -> tuple[int, str]:
        try:
            return (int(turn), turn)
        except ValueError:
            return (0, turn)

    async def cleanup_session(self, session_id: str, *, history_ttl: int = HISTORY_TTL_SECONDS) -> None:
        meta = await self.get_meta(session_id)
        actor_ids = self.actor_ids_from_meta(meta or {})
        client = self._client()
        async with client.pipeline(transaction=False) as pipe:
            pipe.delete(self.targets_key(session_id))
            pipe.delete(self.action_queue_key(session_id))
            pipe.delete(self.busy_lock_key(session_id))
            for actor_id in actor_ids:
                pipe.delete(self.actor_key(session_id, actor_id))
                pipe.delete(self.moves_key(session_id, actor_id))
            pipe.expire(self.meta_key(session_id), history_ttl)
            pipe.expire(self.log_key(session_id), history_ttl)
            await pipe.execute()

    async def acquire_busy_lock(self, session_id: str, owner: str, *, ttl: int = 60) -> bool:
        return bool(await self._client().set(self.busy_lock_key(session_id), owner, nx=True, ex=ttl))

    async def release_busy_lock(self, session_id: str, owner: str) -> None:
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        end
        return 0
        """
        await self._client().eval(script, 1, self.busy_lock_key(session_id), owner)

    async def acquire_worker_lock(self, session_id: str, worker_id: str) -> bool:
        """Acquires a distributed lock for a specific worker/task."""
        script = """
        local val = redis.call('GET', KEYS[1])
        if val == 'pending' or not val then
            redis.call('SET', KEYS[1], ARGV[1], 'EX', 60)
            return 1
        end
        return 0
        """
        return bool(await self._client().eval(script, 1, self.busy_lock_key(session_id), worker_id))

    async def check_worker_lock(self, session_id: str, worker_id: str) -> bool:
        """Checks if the lock is still held by the current worker."""
        val = await self._client().get(self.busy_lock_key(session_id))
        return self._decode(val) == worker_id

    async def release_worker_lock_safe(self, session_id: str, worker_id: str) -> None:
        """Releases the lock only if it is still owned by the current worker."""
        await self.release_busy_lock(session_id, worker_id)

    async def check_and_lock_busy_for_collector(self, session_id: str) -> bool:
        """Initial short-term lock for the collector to prevent multiple concurrent collections."""
        return await self.acquire_busy_lock(session_id, "pending", ttl=30)

    @staticmethod
    def actor_ids_from_meta(meta: dict[str, Any]) -> list[str]:
        teams = CombatSessionManager.decode_json_field(meta.get("teams"), default={})
        actor_ids: list[str] = []
        if isinstance(teams, dict):
            for members in teams.values():
                actor_ids.extend(str(actor_id) for actor_id in members)
        return actor_ids

    @staticmethod
    def decode_json_field(value: Any, *, default: Any) -> Any:
        if value in (None, ""):
            return default
        if isinstance(value, dict | list):
            return value
        try:
            return json.loads(str(value))
        except json.JSONDecodeError:
            return default

    @staticmethod
    def _first(result: Any) -> Any:
        if isinstance(result, list):
            return result[0] if result else None
        return result

    @staticmethod
    def _first_dict(result: Any) -> dict[str, Any] | None:
        value = CombatSessionManager._first(result)
        return value if isinstance(value, dict) else None

    @staticmethod
    def _decode(value: Any) -> Any:
        return value.decode() if isinstance(value, bytes) else value

    @staticmethod
    def _json_member_path(member: str | int) -> str:
        escaped = str(member).replace("\\", "\\\\").replace('"', '\\"')
        return f'$["{escaped}"]'

    @staticmethod
    def _redis_value(value: Any) -> str | int | float:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, str | int | float):
            return value
        return json.dumps(value)
