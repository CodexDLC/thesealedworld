class RedisKeys:
    """
    Предоставляет статические методы для генерации стандартизированных ключей Redis.

    Этот класс гарантирует, что все компоненты приложения используют
    единый формат для ключей Redis, что упрощает управление данными
    и предотвращает конфликты.
    """

    # RBC (Reactive Burst Combat) Keys
    @staticmethod
    def get_rbc_actor_key(session_id: str, char_id: int | str) -> str:
        """
        RBC: Генерирует ключ для HASH конкретного актора.
        Содержит поля v:raw, s:hp, s:belt и т.д.
        """
        return f"combat:rbc:{session_id}:actor:{char_id}"

    @staticmethod
    def get_combat_actors_key(session_id: str) -> str:
        """
        RBC: (DEPRECATED/UNUSED in v2.0)
        В новой схеме каждый актор имеет свой ключ.
        Оставляем для совместимости, если где-то еще используется, но лучше удалить.
        """
        return f"combat:rbc:{session_id}:actors"

    @staticmethod
    def get_combat_moves_key(session_id: str, char_id: int | str) -> str:
        """
        RBC: Генерирует ключ для HASH, хранящего "пули" одного игрока (CombatMoveDTO).
        Поле: target_id, Значение: JSON DTO.
        """
        return f"combat:rbc:{session_id}:moves:{char_id}"

    @staticmethod
    def get_combat_exchanges_key(session_id: str, char_id: int | str) -> str:
        """
        RBC: Генерирует ключ для LIST, хранящего очередь ID противников для одного игрока.
        """
        return f"combat:rbc:{session_id}:exchanges:{char_id}"

    @staticmethod
    def get_rbc_meta_key(session_id: str) -> str:
        """
        RBC: Генерирует ключ для HASH, хранящего метаданные сессии (active, winner, mode).
        """
        return f"combat:rbc:{session_id}:meta"

    @staticmethod
    def get_combat_log_key(session_id: str) -> str:
        """
        RBC: Генерирует ключ для хранения логов боевой сессии (тип LIST).
        """
        return f"combat:rbc:{session_id}:logs"

    @staticmethod
    def get_rbc_queue_key(session_id: str) -> str:
        """
        RBC: Генерирует ключ для глобальной очереди задач сессии (тип LIST).
        """
        return f"combat:rbc:{session_id}:q:actions"

    @staticmethod
    def get_rbc_targets_key(session_id: str) -> str:
        """
        RBC: Генерирует ключ для глобального JSON с очередями целей.
        """
        return f"combat:rbc:{session_id}:targets"

    # --- Session Keys (Scenario, Inventory, etc.) ---

    @staticmethod
    def get_scenario_session_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения данных сессии сценария (тип HASH).
        """
        return f"scen:session:{char_id}:data"

    @staticmethod
    def get_inventory_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения данных сессии инвентаря (тип JSON).
        Format: ac:{char_id}:inventory
        """
        return f"ac:{char_id}:inventory"

    @staticmethod
    def get_lobby_session_key(user_id: int) -> str:
        """
        Генерирует ключ для хранения данных сессии лобби (список персонажей).
        Тип: STRING (JSON)
        """
        return f"lobby_session:{user_id}"

    @staticmethod
    def get_onboarding_draft_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения черновика создания персонажа.
        Тип: STRING (JSON)
        """
        return f"onboarding_draft:{char_id}"

    # --- Legacy Keys ---

    @staticmethod
    def get_account_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения динамических данных аккаунта персонажа в Redis (тип HASH).
        """
        return f"ac:{char_id}"

    @staticmethod
    def get_world_location_meta_key(loc_id: str) -> str:
        """
        Генерирует ключ для хранения статичных метаданных мировой локации (тип HASH).
        """
        return f"world:loc:{loc_id}"

    @staticmethod
    def get_world_location_players_key(loc_id: str) -> str:
        """
        Генерирует ключ для хранения идентификаторов игроков, находящихся в данной локации (тип SET).
        """
        return f"world:players_loc:{loc_id}"

    @staticmethod
    def get_world_location_battles_key(loc_id: str) -> str:
        """
        Генерирует ключ для хранения идентификаторов активных боев в данной локации (тип SET).
        """
        return f"world:battles_loc:{loc_id}"

    @staticmethod
    def get_solo_dungeon_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения состояния одиночного подземелья (тип HASH).
        """
        return f"s_d:{char_id}"

    @staticmethod
    def get_group_dungeon_key(instance_id: str) -> str:
        """
        Генерирует ключ для хранения состояния группового подземелья (тип HASH).
        """
        return f"g_d:{instance_id}"

    @staticmethod
    def get_combat_actor_key(session_id: str, char_id: int) -> str:
        """
        (Legacy) Генерирует ключ для хранения данных конкретного участника боевой сессии.
        """
        return f"combat:sess:{session_id}:actor:{char_id}"

    @staticmethod
    def get_combat_pending_move_key(session_id: str, actor_id: int, target_id: int) -> str:
        """
        (Legacy) Генерирует ключ для хранения информации о незавершенном ходе.
        """
        return f"combat:sess:{session_id}:pending:{actor_id}:{target_id}"

    @staticmethod
    def get_combat_pending_move_pattern(session_id: str, actor_id: int) -> str:
        """
        (Legacy) Генерирует паттерн для поиска всех незавершенных ходов.
        """
        return f"combat:sess:{session_id}:pending:{actor_id}:*"

    @staticmethod
    def get_combat_meta_key(session_id: str) -> str:
        """
        (Legacy) Генерирует ключ для хранения метаданных боевой сессии (тип HASH).
        """
        return f"combat:sess:{session_id}:meta"

    @staticmethod
    def get_combat_participants_key(session_id: str) -> str:
        """
        (Legacy) Генерирует ключ для хранения идентификаторов всех участников боевой сессии (тип SET).
        """
        return f"combat:sess:{session_id}:participants"

    @staticmethod
    def get_arena_queue_key(mode: str) -> str:
        """
        Генерирует ключ для очереди арены (тип ZSET).
        """
        return f"arena:queue:{mode}:zset"

    @staticmethod
    def get_arena_request_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения метаданных заявки персонажа на арену (тип HASH/STRING).
        """
        return f"arena:req:{char_id}"

    @staticmethod
    def get_player_status_key(char_id: int) -> str:
        """
        Генерирует ключ для хранения текущего статуса игрока для межсервисного взаимодействия.
        """
        return f"player:status:{char_id}"
