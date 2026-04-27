# apps/shared/enums/stats_enum.py
from enum import StrEnum


class PrimaryStat(StrEnum):
    """
    Перечисление первичных атрибутов (статов) сущностей.
    Используется как единый источник правды для определения,
    является ли характеристика базовым атрибутом.
    """

    STRENGTH = "strength"
    AGILITY = "agility"
    ENDURANCE = "endurance"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    MEN = "men"
    PERCEPTION = "perception"
    CHARISMA = "charisma"
    LUCK = "luck"
