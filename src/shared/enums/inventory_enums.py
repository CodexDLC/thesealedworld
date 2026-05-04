from enum import StrEnum


class InventoryViewTarget(StrEnum):
    """
    Типы экранов инвентаря (для навигации).
    """

    MAIN = "main"  # Главный экран (Кукла)
    BAG = "bag"  # Сумка (Сетка предметов)
    DETAILS = "details"  # Детали предмета


class InventoryActionType(StrEnum):
    """
    Типы действий с предметами.
    """

    EQUIP = "equip"
    UNEQUIP = "unequip"
    USE = "use"
    MOVE = "move"  # Перемещение (в быстрый слот или другую ячейку)
    DROP = "drop"  # Удаление предмета


class InventorySection(StrEnum):
    """
    Разделы сумки (фильтры верхнего уровня).
    """

    EQUIPMENT = "equipment"
    CONSUMABLE = "consumable"
    RESOURCE = "resource"
    QUEST = "quest"
