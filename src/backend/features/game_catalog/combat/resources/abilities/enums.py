from enum import StrEnum


class AbilitySource(StrEnum):
    COMBAT = "combat"  # Боевой прием / трата боевых токенов
    GIFT = "gift"  # Дар (Energy + Gift Token)
    ITEM = "item"  # Предмет (Свиток, Зелье)


class AbilityType(StrEnum):
    INSTANT = "instant"  # Мгновенное действие (в свой ход)
    REACTION = "reaction"  # Ответное действие (в чужой ход / триггер)
    PASSIVE = "passive"  # Пассивный эффект (всегда активен)
