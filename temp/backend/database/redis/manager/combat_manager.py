import json
from typing import Any

from loguru import logger as log
from redis.asyncio.client import Pipeline

from src.backend.database.redis.redis_key import RedisKeys as Rk
from src.backend.database.redis.redis_service import RedisService
from src.backend.domains.user_features.combat.dto import SessionDataDTO


class CombatManager:
    """
    Менеджер для управления данными боевых сессий в Redis (RBC v3.0).
    Инкапсулирует ключи и методы доступа к данным.
    """

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service

    # ==========================================================================
    # 1. ГЛОБАЛЬНОЕ СОСТОЯНИЕ (META & TARGETS)
    # ==========================================================================

    async def get_rbc_session_meta(self, session_id: str) -> dict[str, str] | None:
        """Загрузка HASH :meta"""
        return await self.redis.get_all_hash(Rk.get_rbc_meta_key(session_id))

    async def set_winner(self, session_id: str, winner: str) -> None:
        """
        Устанавливает победителя и завершает бой (active=0).
        """
        key = Rk.get_rbc_meta_key(session_id)
        await self.redis.redis_client.hset(key, mapping={"active": 0, "winner": winner, "status": "finished"})  # type: ignore

    async def pop_player_target(self, session_id: str, char_id: int | str) -> int | None:
        """
        [ATOMIC] Извлекает (Pop) первую цель из персонального пула :targets.
        """
        key = Rk.get_rbc_targets_key(session_id)
        # JSON.ARRPOP позволяет атомарно забрать ID цели из массива по пути $.char_id
        res = await self.redis.eval_script(
            "return redis.call('JSON.ARRPOP', KEYS[1], '$.' .. ARGV[1], 0)", keys=[key], args=[str(char_id)]
        )
        return int(res[0]) if res and res[0] else None

    async def peek_player_target(self, session_id: str, char_id: int | str) -> int | None:
        """
        Возвращает первую цель из очереди, НЕ удаляя ее (PEEK).
        Используется для ViewService.
        """
        key = Rk.get_rbc_targets_key(session_id)
        # JSON.GET path $.char_id[0]
        res = await self.redis.json_get(key, f"$.{char_id}[0]")

        if res and isinstance(res, list) and len(res) > 0 and res[0] is not None:
            return int(res[0])
        return None

    async def create_session_batch(self, session_id: str, data: SessionDataDTO, ttl: int) -> None:
        """
        Создает сессию в Redis (Meta, Targets, Actors).
        """

        def _fill_pipe(pipe: Pipeline) -> None:
            # 1. Global Meta (Hash)
            pipe.hset(Rk.get_rbc_meta_key(session_id), mapping=data.meta)
            pipe.expire(Rk.get_rbc_meta_key(session_id), ttl)

            # 2. Global Targets (JSON)
            targets_key = Rk.get_rbc_targets_key(session_id)
            pipe.json().set(targets_key, "$", data.targets)  # type: ignore
            pipe.expire(targets_key, ttl)

            # 3. Actors (Namespace)
            for aid, actor_data in data.actors.items():
                base_key = Rk.get_rbc_actor_key(session_id, str(aid))

                # Unified JSON Key
                pipe.json().set(base_key, "$", actor_data)  # type: ignore
                pipe.expire(base_key, ttl)

                # :moves (JSON) - Init with empty dicts
                moves_key = Rk.get_combat_moves_key(session_id, str(aid))
                empty_moves: dict[str, dict[str, Any]] = {"exchange": {}, "item": {}, "instant": {}}
                pipe.json().set(moves_key, "$", empty_moves)  # type: ignore
                pipe.expire(moves_key, ttl)

        await self.redis.execute_pipeline(_fill_pipe)
        log.info(f"CombatManager | action=create_session status=success session_id={session_id}")

    async def universal_hot_join(
        self, session_id: str, char_id: int | str, team_name: str, actor_data: dict, is_ai: bool = True
    ) -> None:
        """
        [UNIVERSAL HOT-JOIN] Атомарно внедряет любого актера (игрока, бота, хаос) в текущую сессию.
        """

        # 1. Создаем инфраструктуру (Pipeline)
        def _fill_pipe(pipe: Pipeline) -> None:
            base = Rk.get_rbc_actor_key(session_id, str(char_id))

            # Unified JSON Key
            pipe.json().set(base, "$", actor_data)  # type: ignore

            moves_key = Rk.get_combat_moves_key(session_id, str(char_id))
            pipe.json().set(moves_key, "$", {"exchange": {}, "item": {}, "instant": {}})  # type: ignore

        await self.redis.execute_pipeline(_fill_pipe)

        # 2. Lua-скрипт для "склейки" социальных связей
        script = """
        local meta_key = KEYS[1]
        local targets_key = KEYS[2]
        local char_id = ARGV[1]
        local team_name = ARGV[2]
        local is_ai = ARGV[3]
        
        -- A. Обновляем actors_info
        local info_raw = redis.call("HGET", meta_key, "actors_info")
        local info = cjson.decode(info_raw or "{}")
        info[char_id] = (is_ai == "1") and "ai" or "player"
        redis.call("HSET", meta_key, "actors_info", cjson.encode(info))
        
        -- B. Обновляем teams
        local teams_raw = redis.call("HGET", meta_key, "teams")
        local teams = cjson.decode(teams_raw or "{}")
        if not teams[team_name] then teams[team_name] = {} end
        
        -- Проверка на дубликат в команде (на всякий случай)
        local exists = false
        for _, id in ipairs(teams[team_name]) do
            if tostring(id) == char_id then exists = true break end
        end
        if not exists then
            table.insert(teams[team_name], tonumber(char_id) or char_id)
            redis.call("HSET", meta_key, "teams", cjson.encode(teams))
        end
        
        -- C. РЕЗОЛВИНГ ЦЕЛЕЙ (Targets)
        -- Мы берем ВСЕ текущие списки целей и добавляем туда нового врага
        local targets_raw = redis.call("JSON.GET", targets_key, "$")
        local all_targets = {}
        if targets_raw then
            all_targets = cjson.decode(targets_raw)[1] or {}
        end
        
        local new_actor_targets = {}
        
        for actor_id, target_list in pairs(all_targets) do
            -- Определяем команду этого актера (нужно найти его в teams)
            
            local is_enemy = true
            -- Проверяем, есть ли он в нашей команде
            if teams[team_name] then
                for _, member_id in ipairs(teams[team_name]) do
                    if tostring(member_id) == actor_id then 
                        is_enemy = false 
                        break 
                    end
                end
            end
            
            if is_enemy then
                -- Мы добавляем себя ему в список целей (если еще нет)
                local already_target = false
                for _, tid in ipairs(target_list) do
                    if tostring(tid) == char_id then already_target = true break end
                end
                if not already_target then
                    table.insert(target_list, tonumber(char_id) or char_id)
                end
                
                -- Он добавляется к нам в список целей
                table.insert(new_actor_targets, tonumber(actor_id) or actor_id)
            end
        end
        
        -- Записываем обновленные списки обратно
        all_targets[char_id] = new_actor_targets
        redis.call("JSON.SET", targets_key, "$", cjson.encode(all_targets))
        
        return 1
        """

        await self.redis.eval_script(
            script,
            keys=[Rk.get_rbc_meta_key(session_id), Rk.get_rbc_targets_key(session_id)],
            args=[str(char_id), team_name, "1" if is_ai else "0"],
        )
        log.info(f"CombatManager | action=hot_join status=success session_id={session_id} char_id={char_id}")

    async def add_log(self, session_id: str, text: str, tags: list[str] | None = None) -> None:
        """Добавляет запись в лог боя."""
        import time

        log_msg = {"text": text, "timestamp": time.time(), "tags": tags or []}
        await self.redis.push_to_list(Rk.get_combat_log_key(session_id), json.dumps(log_msg))

    # ==========================================================================
    # 2. ДАННЫЕ АКТОРА (BATCH LOADING)
    # ==========================================================================

    async def load_full_context_data(self, session_id: str, char_ids: list[int | str]) -> dict[str, Any]:
        """
        Загружает данные всех участников сессии.
        Возвращает структурированный словарь: {char_id: {state, raw, loadout, ...}}
        """
        raw_results = await self.load_actors_data_batch(session_id, char_ids)

        step = 2  # Actor JSON + Moves JSON
        structured_data: dict[str, Any] = {}
        for i, cid in enumerate(char_ids):
            idx = i * step

            # Convert cid to string for consistency as dict key
            cid_str = str(cid)

            actor_data = raw_results[idx]
            moves_data = raw_results[idx + 1]

            if not actor_data:
                # Fallback if actor not found
                structured_data[cid_str] = {
                    "state": {},
                    "raw": {},
                    "loadout": {},
                    "meta": {},
                    "statuses": {"abilities": [], "effects": []},  # NEW: Default statuses
                    "xp": {},
                    "move": {},
                }
                continue

            # Extract fields from unified JSON
            # Note: state is now inside meta
            meta = actor_data.get("meta", {})
            state = {
                "hp": meta.get("hp", 0),
                "max_hp": meta.get("max_hp", 0),
                "en": meta.get("en", 0),
                "max_en": meta.get("max_en", 0),
                "tactics": meta.get("tactics", 0),
                "afk_level": meta.get("afk_level", 0),
                "is_dead": meta.get("is_dead", False),
                "tokens": meta.get("tokens", {}),
            }

            structured_data[cid_str] = {
                "state": state,
                "raw": actor_data.get("raw", {}),
                "loadout": actor_data.get("loadout", {}),
                "meta": meta,
                "statuses": actor_data.get("statuses", {"abilities": [], "effects": []}),  # NEW: Read statuses
                "xp": actor_data.get("xp_buffer", {}),
                "skills": actor_data.get("skills", {}),
                "move": moves_data if moves_data else {},
            }

        structured_data["global_queue"] = raw_results[-1]
        return structured_data

    async def load_actors_data_batch(self, session_id: str, char_ids: list[int | str]) -> list[Any]:
        """
        Пакетная загрузка всех данных актеров (2 ключа на каждого).
        """

        def _load_batch(pipe: Pipeline) -> None:
            for cid in char_ids:
                base_key = Rk.get_rbc_actor_key(session_id, str(cid))
                # 1. Unified Actor JSON
                pipe.json().get(base_key)  # type: ignore
                # 2. Moves (Intents)
                pipe.json().get(Rk.get_combat_moves_key(session_id, str(cid)))  # type: ignore

            pipe.lrange(Rk.get_rbc_queue_key(session_id), 0, -1)

        return await self.redis.execute_pipeline(_load_batch)

    async def load_snapshot_data_batch(
        self, session_id: str, char_ids: list[int | str]
    ) -> tuple[dict[str, list[int]], list[Any]]:
        """
        Легкая загрузка для UI (Targets + Actors Data).
        Возвращает (targets_map, actors_data_list).
        """

        def _load(pipe: Pipeline) -> None:
            # 1. Targets
            pipe.json().get(Rk.get_rbc_targets_key(session_id))  # type: ignore

            # 2. Actors
            for cid in char_ids:
                base_key = Rk.get_rbc_actor_key(session_id, str(cid))
                # Load specific fields to reduce bandwidth
                pipe.json().get(base_key, "$.meta", "$.loadout", "$.statuses")  # type: ignore # NEW: $.statuses
                pipe.json().get(Rk.get_combat_moves_key(session_id, str(cid)))  # type: ignore

        results = await self.redis.execute_pipeline(_load)

        targets_raw = results[0]
        targets_map = {}
        if targets_raw:
            for k, v in targets_raw.items():
                # Keys in JSON are always strings
                targets_map[str(k)] = v

        # Process actor results
        # Results structure: [targets, actor1_data, actor1_moves, actor2_data, actor2_moves, ...]
        actors_data_list = []
        raw_actor_results = results[1:]

        for i in range(0, len(raw_actor_results), 2):
            actor_partial = raw_actor_results[i]  # Dict with keys from JSONPath
            moves = raw_actor_results[i + 1]

            if actor_partial:
                # RedisJSON returns dict like { "$.meta": [...], "$.loadout": [...] }
                # We need to flatten it
                meta = actor_partial.get("$.meta", [{}])[0]
                loadout = actor_partial.get("$.loadout", [{}])[0]
                statuses = actor_partial.get("$.statuses", [{"abilities": [], "effects": []}])[0]  # NEW: statuses

                # Reconstruct partial object for UI
                actors_data_list.append({"meta": meta, "loadout": loadout, "statuses": statuses, "moves": moves})
            else:
                actors_data_list.append(None)  # type: ignore

        return targets_map, actors_data_list

    # ==========================================================================
    # 3. НАМЕРЕНИЯ (MOVES - MULTI-TARGETING)
    # ==========================================================================

    async def append_move(self, session_id: str, char_id: int | str, strategy: str, move_dto: dict) -> None:
        """
        [SPAMMING] Добавляет намерение в СЛОВАРЬ соответствующей стратегии.
        strategy: 'exchange', 'item', 'instant'
        """
        key = Rk.get_combat_moves_key(session_id, str(char_id))
        move_id = move_dto.get("move_id")
        if not move_id:
            raise ValueError("Move DTO must have move_id")

        # Путь: $.strategy.move_id
        path = f"$.{strategy}.{move_id}"

        # Используем JSON.SET для записи в словарь
        await self.redis.json_set(key, path, move_dto)

        # Обновляем TTL ключа (продлеваем жизнь всем намерениям)
        await self.redis.expire(key, 300)

    async def append_moves_batch(self, session_id: str, char_id: int | str, moves_dtos: list[Any]) -> None:
        """
        [BATCH] Добавляет несколько намерений (без удаления целей).
        Используется для Instant/Item мувов AI.
        """

        def _save_batch(pipe: Pipeline) -> None:
            key = Rk.get_combat_moves_key(session_id, str(char_id))
            for move in moves_dtos:
                path = f"$.{move.strategy}.{move.move_id}"
                pipe.json().set(key, path, move.model_dump())  # type: ignore
            pipe.expire(key, 300)

        await self.redis.execute_pipeline(_save_batch)

    async def register_exchange_move_atomic(
        self, session_id: str, char_id: int | str, target_id: int | str, move_dto: dict
    ) -> bool:
        """
        [ATOMIC] Регистрирует ход типа 'exchange'.
        """
        targets_key = Rk.get_rbc_targets_key(session_id)
        moves_key = Rk.get_combat_moves_key(session_id, str(char_id))

        move_id = move_dto.get("move_id")
        if not move_id:
            return False

        # LUA Script
        script = """
        local targets = redis.call('JSON.GET', KEYS[1], '$.' .. ARGV[1])
        if not targets then return 0 end
        
        -- ARGV[2] (target_id) can be string or int. JSON.ARRINDEX handles types strictly.
        -- We try both number and string if needed, but usually we pass string here.
        
        local idx_res = redis.call('JSON.ARRINDEX', KEYS[1], '$.' .. ARGV[1], tonumber(ARGV[2]) or ARGV[2])
        
        if not idx_res or idx_res[1] == -1 then
            return 0
        end
        
        local real_idx = idx_res[1]
        
        -- 1. Удаляем цель (POP по индексу)
        redis.call('JSON.ARRPOP', KEYS[1], '$.' .. ARGV[1], real_idx)
        
        -- 2. Добавляем ход (JSON.SET в словарь)
        -- Путь: $.exchange.move_id
        local path = '$.exchange.' .. ARGV[4]
        redis.call('JSON.SET', KEYS[2], path, ARGV[3])
        
        return 1
        """

        import json

        res = await self.redis.eval_script(
            script,
            keys=[targets_key, moves_key],
            args=[str(char_id), str(target_id), json.dumps(move_dto), str(move_id)],
        )
        return bool(res)

    async def register_moves_batch_atomic(
        self, session_id: str, char_id: int | str, moves_data: list[dict[str, Any]]
    ) -> int:
        """
        [ATOMIC BATCH] Регистрирует несколько ходов для AI.
        """
        if not moves_data:
            return 0

        targets_key = Rk.get_rbc_targets_key(session_id)
        moves_key = Rk.get_combat_moves_key(session_id, str(char_id))

        # LUA Script
        script = """
        local success_count = 0
        local moves = cjson.decode(ARGV[2])
        local char_id = ARGV[1]
        
        for _, move_item in ipairs(moves) do
            local target_id = move_item.target_id
            local move_json = move_item.move_json
            local strategy = move_item.strategy
            local move_id = move_item.move_id
            
            -- 1. Ищем цель (try number then string)
            local idx_res = redis.call('JSON.ARRINDEX', KEYS[1], '$.' .. char_id, tonumber(target_id) or target_id)
            
            if idx_res and idx_res[1] ~= -1 then
                local real_idx = idx_res[1]
                
                -- 2. Удаляем цель
                redis.call('JSON.ARRPOP', KEYS[1], '$.' .. char_id, real_idx)
                
                -- 3. Записываем мув
                local path = '$.' .. strategy .. '.' .. move_id
                redis.call('JSON.SET', KEYS[2], path, move_json)
                
                success_count = success_count + 1
            end
        end
        
        return success_count
        """

        import json

        res = await self.redis.eval_script(
            script, keys=[targets_key, moves_key], args=[str(char_id), json.dumps(moves_data)]
        )
        return int(res) if res else 0

    async def check_move_exists(self, session_id: str, char_id: int | str) -> bool:
        """Проверяет наличие ключа с намерениями."""
        key = Rk.get_combat_moves_key(session_id, str(char_id))
        return await self.redis.key_exists(key)

    async def get_moves_batch(self, session_id: str, char_ids: list[int | str]) -> dict[str, Any]:
        """Загружает только moves для списка игроков."""

        def _load(pipe: Pipeline) -> None:
            for cid in char_ids:
                pipe.json().get(Rk.get_combat_moves_key(session_id, str(cid)))  # type: ignore

        results = await self.redis.execute_pipeline(_load)
        return {str(cid): res for cid, res in zip(char_ids, results, strict=False) if res}

    async def push_actions_batch(self, session_id: str, actions_json: list[str]) -> None:
        """Запись резолвленных задач в системную очередь q:actions."""
        if not actions_json:
            return
        key = Rk.get_rbc_queue_key(session_id)

        def _push(pipe: Pipeline) -> None:
            pipe.rpush(key, *actions_json)

        await self.redis.execute_pipeline(_push)

    async def get_queue_size(self, session_id: str) -> int:
        """Возвращает текущий размер очереди действий."""
        key = Rk.get_rbc_queue_key(session_id)
        return await self.redis.redis_client.llen(key)  # type: ignore

    async def transfer_intents_to_actions(
        self, session_id: str, actions_json: list[str], deletes: list[dict[str, Any]]
    ) -> None:
        """
        [ATOMIC] Переносит резолвленные намерения (Intents) в очередь действий (Actions).
        """
        if not actions_json and not deletes:
            return

        def _fill_pipe(pipe: Pipeline) -> None:
            # 1. Добавляем в системную очередь сессии q:actions
            if actions_json:
                queue_key = Rk.get_rbc_queue_key(session_id)
                pipe.rpush(queue_key, *actions_json)

            # 2. Удаляем пули из хранилища намерений игрока
            for item in deletes:
                moves_key = Rk.get_combat_moves_key(session_id, str(item["char_id"]))
                # Путь удаления: $.exchange.uuid_1
                path = f"$.{item['strategy']}.{item['move_id']}"
                pipe.json().delete(moves_key, path)  # type: ignore
                # Продлеваем TTL
                pipe.expire(moves_key, 300)

        await self.redis.execute_pipeline(_fill_pipe)

    # ==========================================================================
    # 4. БЛОКИРОВКА (BUSY LOCK)
    # ==========================================================================

    async def check_and_lock_busy_for_collector(self, session_id: str) -> bool:
        """
        Проверяет, свободна ли сессия. Если свободна — резервирует её для воркера.
        """
        key = f"combat:rbc:{session_id}:sys:busy"
        return await self.redis.redis_client.set(key, "pending", nx=True, ex=30)  # type: ignore

    async def acquire_worker_lock(self, session_id: str, worker_id: str) -> bool:
        """
        [WORKER] Захват лока (перезапись pending).
        """
        key = f"combat:rbc:{session_id}:sys:busy"
        script = """
        local val = redis.call('GET', KEYS[1])
        if val == 'pending' or not val then
            redis.call('SET', KEYS[1], ARGV[1], 'EX', 60)
            return 1
        end
        return 0
        """
        res = await self.redis.eval_script(script, keys=[key], args=[worker_id])
        return bool(res)

    async def check_worker_lock(self, session_id: str, worker_id: str) -> bool:
        """
        [WORKER] Проверка, что лок все еще принадлежит нам.
        """
        key = f"combat:rbc:{session_id}:sys:busy"
        val = await self.redis.get_value(key)
        return val == worker_id

    async def release_worker_lock_safe(self, session_id: str, worker_id: str) -> None:
        """
        [WORKER] Снятие лока только если он наш.
        """
        key = f"combat:rbc:{session_id}:sys:busy"
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval_script(script, keys=[key], args=[worker_id])

    # ==========================================================================
    # 5. КОММИТ (BATCH SAVING)
    # ==========================================================================

    async def commit_battle_results(
        self,
        session_id: str,
        updates: dict,
        logs: list[str],
        processed_count: int,
        target_returns: list[dict[str, int]] | None = None,
        dead_actors: str | None = None,  # ← НОВЫЙ ПАРАМЕТР (JSON string)
    ) -> None:
        """
        Массовое сохранение итогов раунда через Pipeline.

        АТОМАРНО выполняет:
        - Обновление состояний акторов (HP, EN, XP, статусы)
        - Запись логов
        - Удаление обработанных действий из очереди
        - Возврат целей в очереди участников (если target_returns передан)
        - Обновление списка мертвых акторов (если dead_actors передан)
        """

        def _commit(pipe: Pipeline) -> None:
            # 1. Сохранение состояний акторов
            for cid, data in updates.items():
                base = f"{Rk.get_rbc_actor_key(session_id, str(cid))}"

                if "state" in data:
                    pipe.json().merge(base, "$.meta", data["state"])  # type: ignore

                if "statuses" in data:
                    pipe.json().set(base, "$.statuses", data["statuses"])  # type: ignore

                if "xp" in data:
                    pipe.json().set(base, "$.xp_buffer", data["xp"])  # type: ignore

                if "raw" in data:
                    pipe.json().set(base, "$.raw", data["raw"])  # type: ignore

                if "raw_temp" in data:
                    pipe.json().set(base, "$.raw.temp", data["raw_temp"])  # type: ignore

            # 2. Логи
            if logs:
                pipe.rpush(Rk.get_combat_log_key(session_id), *logs)

            # 3. Удаление обработанных действий
            if processed_count > 0:
                pipe.ltrim(Rk.get_rbc_queue_key(session_id), processed_count, -1)

            # 4. НОВОЕ: Возврат целей (атомарно в одной транзакции)
            if target_returns:
                targets_key = Rk.get_rbc_targets_key(session_id)
                for pair in target_returns:
                    source_id = str(pair["source_id"])
                    target_id = pair["target_id"]
                    pipe.json().arrappend(targets_key, f"$.{source_id}", target_id)  # type: ignore

            # 5. НОВОЕ: Обновление списка мертвых акторов
            if dead_actors:
                meta_key = Rk.get_rbc_meta_key(session_id)
                pipe.hset(meta_key, "dead_actors", dead_actors)

        await self.redis.execute_pipeline(_commit)
        log.info(f"CombatManager | action=commit_results status=success session_id={session_id}")

    # ==========================================================================
    # 6. ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================================

    async def get_actor_state(self, session_id: str, char_id: int | str) -> dict[str, Any] | None:
        """
        Возвращает state (из meta)
        """
        key = Rk.get_rbc_actor_key(session_id, str(char_id))
        # Fetch only meta part
        meta = await self.redis.json_get(key, "$.meta")
        if meta and isinstance(meta, list) and meta[0]:
            # Extract state-like fields from meta
            m = meta[0]
            return {
                "hp": m.get("hp"),
                "max_hp": m.get("max_hp"),
                "en": m.get("en"),
                "max_en": m.get("max_en"),
                "tactics": m.get("tactics"),
                "is_dead": m.get("is_dead"),
                "tokens": m.get("tokens"),
                "afk_level": m.get("afk_level"),
                "feints": m.get("feints"),  # NEW: Need feints for validation
            }
        return None

    async def get_actor_raw(self, session_id: str, char_id: int | str) -> dict[str, Any] | None:
        key = Rk.get_rbc_actor_key(session_id, str(char_id))
        data = await self.redis.json_get(key, "$.raw")
        if isinstance(data, list) and data:
            return data[0]
        return None

    async def get_combat_log_list(self, session_id: str) -> list[str]:
        key = Rk.get_combat_log_key(session_id)
        return await self.redis.get_list_range(key)

    async def cleanup_rbc_session(self, session_id: str, history_ttl: int = 86400) -> None:
        def _cleanup(pipe: Pipeline) -> None:
            pipe.delete(Rk.get_rbc_targets_key(session_id))
            pipe.delete(Rk.get_rbc_queue_key(session_id))
            pipe.expire(Rk.get_rbc_meta_key(session_id), history_ttl)
            pipe.expire(Rk.get_combat_log_key(session_id), history_ttl)

        await self.redis.execute_pipeline(_cleanup)
        log.info(f"CombatManager | action=cleanup status=success session_id={session_id}")

    # ==========================================================================
    # 7. FEINT SYSTEM (ATOMIC)
    # ==========================================================================

    async def consume_feint_atomic(self, session_id: str, char_id: int | str, feint_id: str) -> dict[str, int] | None:
        """
        [ATOMIC] Проверяет наличие финта в руке и удаляет его.
        Возвращает стоимость финта (если он был), иначе None.
        """
        key = Rk.get_rbc_actor_key(session_id, str(char_id))

        # Lua Script:
        # 1. Check if feint exists in $.meta.feints.hand
        # 2. If yes, get cost, delete feint, return cost
        # 3. If no, return nil

        script = """
        local key = KEYS[1]
        local feint_id = ARGV[1]
        
        -- Get hand
        local hand_raw = redis.call("JSON.GET", key, "$.meta.feints.hand")
        if not hand_raw then return nil end
        
        local hand = cjson.decode(hand_raw)[1]
        if not hand or not hand[feint_id] then return nil end
        
        local cost = hand[feint_id]
        
        -- Delete feint
        redis.call("JSON.DEL", key, "$.meta.feints.hand." .. feint_id)
        
        return cjson.encode(cost)
        """

        res = await self.redis.eval_script(script, keys=[key], args=[feint_id])

        if res:
            return json.loads(res)
        return None

    async def return_feint_to_hand(
        self, session_id: str, char_id: int | str, feint_id: str, cost: dict[str, int]
    ) -> None:
        """
        Возвращает финт в руку (если атака не прошла).
        """
        key = Rk.get_rbc_actor_key(session_id, str(char_id))
        # JSON.SET $.meta.feints.hand.feint_id = cost
        await self.redis.json_set(key, f"$.meta.feints.hand.{feint_id}", cost)
