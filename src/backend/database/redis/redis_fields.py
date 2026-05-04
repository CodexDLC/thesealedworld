class AccountFields:
    """
    Константы полей внутри Redis-хэша аккаунта (ключ ac:{char_id}).

    Использование этих констант вместо строковых литералов помогает
    избежать опечаток и упрощает рефакторинг имен полей.
    """

    # --- Core State (Состояние движка) ---
    STATE = "state"  # Текущий глобальный стейт (exploration, combats, scenario)
    PREV_STATE = "prev_state"  # Предыдущий стейт (для возврата, например, после данжа)

    # --- Location (Навигация) ---
    LOCATION_ID = "location_id"  # ID текущей локации (например, "52_52" или "town_hall")
    PREV_LOCATION_ID = "prev_location_id"  # ID предыдущей локации (для возврата)

    # --- Session IDs (Активные сессии) ---
    COMBAT_SESSION_ID = "combat_session_id"  # UUID активной боевой сессии
    SCENARIO_SESSION_ID = "scenario_session_id"  # UUID активной сессии сценария
    INVENTORY_SESSION_ID = "inventory_session_id"  # UUID активной сессии инвентаря (фильтры, страницы)
    STATUS_SESSION_ID = "status_session_id"  # UUID активной сессии меню статуса

    # --- Quest & Scenario Metadata ---
    ACTIVE_QUEST_KEY = "active_quest_key"  # Ключ активного квеста (если игрок в сценарии)

    # --- Vitals & Stats (Динамические характеристики) ---
    # Эти данные часто обновляются и читаются из Redis для скорости
    HP_CURRENT = "hp_current"  # Текущее здоровье
    ENERGY_CURRENT = "energy_current"  # Текущая энергия
    LAST_UPDATE = "last_update"  # Timestamp последнего изменения характеристик
