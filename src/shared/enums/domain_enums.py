from enum import StrEnum


class CoreDomain(StrEnum):
    """
    Перечень всех доменов (оркестраторов) системы.
    Включает в себя как игровые стейты (GameState), так и служебные сервисы.
    Используется в CombatGateway для маршрутизации.
    """

    # --- Игровые домены (совпадают с GameState) ---
    EXPLORATION = "exploration"
    INVENTORY = "inventory"
    STATUS = "status"
    COMBAT = "combats"  # Обычно это CombatTurnOrchestrator
    COMBAT_RESULT = "combat_result"
    SCENARIO = "scenario"
    ONBOARDING = "onboarding"
    LOBBY = "lobby"
    ARENA = "arena"
    RIFT = "rift"
    CITY_SERVICES = "city_services"
    DEATH = "death"
    LOOT = "loot"

    # --- Служебные / Специфичные домены ---
    COMBAT_ENTRY = "combat_entry"  # Вход в бой, создание сессии
    MENU = "game_menu"  # Добавлено для Game Menu
    WORLD = "world"  # Управление миром (загрузка, бои в локациях)
