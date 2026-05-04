import json
from typing import Any

from loguru import logger as log
from redis.asyncio.client import Pipeline

from src.backend.database.redis.redis_key import RedisKeys as Rk
from src.backend.database.redis.redis_service import RedisService


class AccountManager:
    """
    Менеджер для управления данными аккаунтов в Redis (ac:{char_id}).
    Использует RedisJSON для хранения структуры.
    Предоставляет методы для работы с конкретными секциями (Bio, Stats, Sessions, etc).
    Также управляет кэшем лобби (lobby:user:{id}).
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    # --- Core Methods (ac:{char_id}) ---

    async def create_account(self, char_id: int, initial_data: dict[str, Any]) -> None:
        """
        Создает запись аккаунта (JSON).

        Args:
            char_id: ID персонажа.
            initial_data: Начальные данные аккаунта.
        """
        key = Rk.get_account_key(char_id)
        # Используем JSON.SET key $ data
        await self.redis_service.json_set(key, "$", initial_data)
        log.info(f"AccountManager | action=create status=success char_id={char_id}")

    async def account_exists(self, char_id: int) -> bool:
        """
        Проверяет существование аккаунта.

        Args:
            char_id: ID персонажа.

        Returns:
            bool: True, если аккаунт существует.
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.key_exists(key)

    async def get_full_account(self, char_id: int) -> dict[str, Any] | None:
        """
        Получает весь JSON аккаунта.

        Args:
            char_id: ID персонажа.

        Returns:
            dict | None: Полные данные аккаунта или None.
        """
        key = Rk.get_account_key(char_id)
        return await self.redis_service.json_get(key, "$")

    async def delete_account(self, char_id: int) -> None:
        """
        Удаляет аккаунт целиком.

        Args:
            char_id: ID персонажа.
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.delete_key(key)
        log.info(f"AccountManager | action=delete status=success char_id={char_id}")

    async def get_account_field(self, char_id: int, field_path: str) -> Any:
        """
        Универсальный геттер для получения поля по JSONPath.

        Args:
            char_id: ID персонажа.
            field_path: Путь к полю (например, "$.bio.name").

        Returns:
            Any: Значение поля.
        """
        key = Rk.get_account_key(char_id)
        # Если путь не начинается с $., добавляем
        if not field_path.startswith("$"):
            field_path = f"$.{field_path}" if not field_path.startswith(".") else f"${field_path}"

        res = await self.redis_service.json_get(key, field_path)
        return res[0] if res else None

    async def update_account_fields(self, char_id: int, updates: dict[str, Any]) -> None:
        """
        Массовое обновление полей.

        Args:
            char_id: ID персонажа.
            updates: Словарь обновлений {"stats": {...}, "state": "SCENARIO"}.
        """
        key = Rk.get_account_key(char_id)

        def _update_batch(pipe: Pipeline) -> None:
            for field, value in updates.items():
                path = f"$.{field}"
                pipe.json().set(key, path, value)  # type: ignore

        await self.redis_service.execute_pipeline(_update_batch)
        log.debug(f"AccountManager | action=update_fields char_id={char_id} fields={list(updates.keys())}")

    # --- Bio ---

    async def get_bio(self, char_id: int) -> dict[str, Any] | None:
        key = Rk.get_account_key(char_id)
        # Возвращает список (так как JSONPath может вернуть несколько), берем первый
        res = await self.redis_service.json_get(key, "$.bio")
        return res[0] if res else None

    async def update_bio(self, char_id: int, bio_data: dict[str, Any]) -> None:
        """
        Обновляет всю секцию bio.
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, "$.bio", bio_data)

    async def update_bio_field(self, char_id: int, field: str, value: Any) -> None:
        """
        Обновляет конкретное поле в bio (например, name).
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, f"$.bio.{field}", value)

    # --- Stats (Vitals) ---

    async def get_stats(self, char_id: int) -> dict[str, Any] | None:
        key = Rk.get_account_key(char_id)
        res = await self.redis_service.json_get(key, "$.stats")
        return res[0] if res else None

    async def update_stat(self, char_id: int, stat_name: str, value: dict[str, int]) -> None:
        """
        Обновляет стат целиком (например, hp: {cur: 100, max: 100}).
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, f"$.stats.{stat_name}", value)

    async def update_stat_current(self, char_id: int, stat_name: str, value: int) -> None:
        """
        Обновляет только текущее значение стата (hp.cur).
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, f"$.stats.{stat_name}.cur", value)

    # --- Attributes ---

    async def get_attributes(self, char_id: int) -> dict[str, int] | None:
        key = Rk.get_account_key(char_id)
        res = await self.redis_service.json_get(key, "$.attributes")
        return res[0] if res else None

    async def update_attributes(self, char_id: int, attributes: dict[str, int]) -> None:
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, "$.attributes", attributes)

    # --- Sessions ---

    async def get_sessions(self, char_id: int) -> dict[str, Any] | None:
        key = Rk.get_account_key(char_id)
        res = await self.redis_service.json_get(key, "$.sessions")
        return res[0] if res else None

    async def set_combat_session(self, char_id: int, session_id: str | None) -> None:
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, "$.sessions.combat_id", session_id)

    async def set_inventory_session(self, char_id: int, session_id: str | None) -> None:
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, "$.sessions.inventory_id", session_id)

    # --- Scenario Integration ---

    async def enter_scenario(self, char_id: int, session_id: str, quest_key: str) -> None:
        """
        Атомарный вход в сценарий.
        Устанавливает state, session_id и active_quest.
        """
        key = Rk.get_account_key(char_id)

        # 1. Получаем текущий стейт для истории
        current_state = await self.get_state(char_id)

        def _enter_batch(pipe: Pipeline) -> None:
            # Сохраняем историю
            if current_state:
                pipe.json().set(key, "$.prev_state", current_state)  # type: ignore

            # Устанавливаем новый контекст
            pipe.json().set(key, "$.state", "SCENARIO")  # type: ignore
            pipe.json().set(key, "$.sessions.scenario_id", session_id)  # type: ignore
            pipe.json().set(key, "$.active_quest", quest_key)  # type: ignore

        await self.redis_service.execute_pipeline(_enter_batch)
        log.info(f"AccountManager | action=enter_scenario char_id={char_id} quest={quest_key}")

    async def leave_scenario(self, char_id: int) -> None:
        """
        Атомарный выход из сценария.
        Сбрасывает state в EXPLORATION и очищает сессию.
        """
        key = Rk.get_account_key(char_id)

        # 1. Получаем текущий стейт (SCENARIO)
        current_state = await self.get_state(char_id)

        def _leave_batch(pipe: Pipeline) -> None:
            if current_state:
                pipe.json().set(key, "$.prev_state", current_state)  # type: ignore

            pipe.json().set(key, "$.state", "EXPLORATION")  # type: ignore
            pipe.json().set(key, "$.sessions.scenario_id", None)  # type: ignore
            pipe.json().set(key, "$.active_quest", None)  # type: ignore

        await self.redis_service.execute_pipeline(_leave_batch)
        log.info(f"AccountManager | action=leave_scenario char_id={char_id}")

    # --- State & Location ---

    async def get_state(self, char_id: int) -> str | None:
        key = Rk.get_account_key(char_id)
        res = await self.redis_service.json_get(key, "$.state")
        return res[0] if res else None

    async def set_state(self, char_id: int, state: str) -> None:
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, "$.state", state)

    async def transition_to_state(self, char_id: int, state: str) -> None:
        """
        Меняет стейт аккаунта с сохранением истории (prev_state).
        """
        key = Rk.get_account_key(char_id)
        current_state = await self.get_state(char_id)

        def _transition_batch(pipe: Pipeline) -> None:
            if current_state:
                pipe.json().set(key, "$.prev_state", current_state)  # type: ignore
            pipe.json().set(key, "$.state", state)  # type: ignore

        await self.redis_service.execute_pipeline(_transition_batch)
        log.info(f"AccountManager | action=transition_state char_id={char_id} new_state={state}")

    async def get_location(self, char_id: int) -> dict[str, Any] | None:
        key = Rk.get_account_key(char_id)
        res = await self.redis_service.json_get(key, "$.location")
        return res[0] if res else None

    async def set_location(self, char_id: int, location_id: str) -> None:
        """
        Обновляет current location.
        """
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, "$.location.current", location_id)

    # --- Metrics ---

    async def get_metrics(self, char_id: int) -> dict[str, Any] | None:
        """Получает все метрики персонажа."""
        key = Rk.get_account_key(char_id)
        res = await self.redis_service.json_get(key, "$.metrics")
        return res[0] if res else None

    async def get_gear_score(self, char_id: int) -> int:
        """Получает GearScore персонажа. Возвращает 0 если не установлен."""
        key = Rk.get_account_key(char_id)
        res = await self.redis_service.json_get(key, "$.metrics.gear_score")
        return res[0] if res and res[0] is not None else 0

    async def set_gear_score(self, char_id: int, value: int) -> None:
        """Устанавливает GearScore персонажа."""
        key = Rk.get_account_key(char_id)
        await self.redis_service.json_set(key, "$.metrics.gear_score", value)

    async def update_metrics(self, char_id: int, updates: dict[str, Any]) -> None:
        """
        Обновляет несколько метрик за раз.
        updates: {"gear_score": 150, "arena_rating": 1200}
        """
        key = Rk.get_account_key(char_id)

        def _metrics_batch(pipe: Pipeline) -> None:
            for field, value in updates.items():
                pipe.json().set(key, f"$.metrics.{field}", value)  # type: ignore

        await self.redis_service.execute_pipeline(_metrics_batch)

    async def increment_metric(self, char_id: int, metric: str, delta: int = 1) -> int:
        """
        Инкрементирует метрику (arena_wins, win_streak, etc.).
        Возвращает новое значение.
        """
        key = Rk.get_account_key(char_id)
        path = f"$.metrics.{metric}"

        # Получаем текущее значение
        res = await self.redis_service.json_get(key, path)
        current = res[0] if res and res[0] is not None else 0

        new_value = current + delta
        await self.redis_service.json_set(key, path, new_value)
        return new_value

    # --- Lobby Cache (lobby:user:{id}) ---

    async def get_lobby_cache(self, user_id: int) -> list[dict[str, Any]] | None:
        """
        Получает кэш лобби (список персонажей).
        """
        key = Rk.get_lobby_session_key(user_id)
        data = await self.redis_service.get_value(key)
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            log.warning(f"AccountManager | action=get_lobby_cache status=failed reason=json_error user_id={user_id}")
            return None

    async def set_lobby_cache(self, user_id: int, characters_data: list[dict[str, Any]]) -> None:
        """
        Сохраняет кэш лобби.
        """
        key = Rk.get_lobby_session_key(user_id)
        data_json = json.dumps(characters_data)
        await self.redis_service.set_value(key, data_json, ttl=600)  # 10 минут

    async def delete_lobby_cache(self, user_id: int) -> None:
        """
        Удаляет кэш лобби.
        """
        key = Rk.get_lobby_session_key(user_id)
        await self.redis_service.delete_key(key)

    # --- Batch Operations (Combat & Context Assembler) ---

    async def bulk_link_combat_session(self, char_ids: list[int], session_id: str) -> None:
        """
        Массово устанавливает combat_session_id для списка персонажей.
        Используется при создании боя.
        """
        if not char_ids:
            return

        def _link_batch(pipe: Pipeline) -> None:
            for cid in char_ids:
                key = Rk.get_account_key(cid)
                pipe.json().set(key, "$.sessions.combat_id", session_id)  # type: ignore

        await self.redis_service.execute_pipeline(_link_batch)
        log.info(f"AccountManager | action=bulk_link_combat char_ids={char_ids} session_id={session_id}")

    async def bulk_unlink_combat_session(self, char_ids: list[int]) -> None:
        """
        Массово очищает combat_session_id для списка персонажей.
        Используется при завершении боя.
        """
        if not char_ids:
            return

        def _unlink_batch(pipe: Pipeline) -> None:
            for cid in char_ids:
                key = Rk.get_account_key(cid)
                pipe.json().set(key, "$.sessions.combat_id", None)  # type: ignore

        await self.redis_service.execute_pipeline(_unlink_batch)
        log.info(f"AccountManager | action=bulk_unlink_combat char_ids={char_ids}")

    async def get_accounts_json_batch(self, char_ids: list[int], path: str = "$") -> list[Any]:
        """
        Пакетная загрузка JSON данных для списка персонажей.
        Используется в PlayerAssembler для получения vitals и других данных.
        """
        if not char_ids:
            return []

        def _load_batch(pipe: Pipeline) -> None:
            for cid in char_ids:
                key = Rk.get_account_key(cid)
                pipe.json().get(key, path)  # type: ignore

        results = await self.redis_service.execute_pipeline(_load_batch)

        # RedisJSON.GET возвращает список значений для каждого пути (даже если путь один)
        # Если path="$", то вернется [full_json_dict]
        # Если path="$.vitals", то вернется [vitals_dict]
        # Нам нужно распаковать эти списки

        unpacked_results = []
        for res in results:
            if res and isinstance(res, list) and len(res) > 0:
                unpacked_results.append(res[0])
            else:
                unpacked_results.append(None)

        return unpacked_results
