from enum import Enum


class AbilitySource(str, Enum):
    GIFT = "gift"  # Дар (Energy + Gift Token)
    ITEM = "item"  # Предмет (Свиток, Зелье)


class AbilityType(str, Enum):
    INSTANT = "instant"  # Мгновенное действие (в свой ход)
    REACTION = "reaction"  # Ответное действие (в чужой ход / триггер)
    PASSIVE = "passive"  # Пассивный эффект (всегда активен)
