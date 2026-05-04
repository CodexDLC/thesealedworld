from enum import Enum

from pydantic import BaseModel, Field


class GiftSchool(str, Enum):
    FIRE = "fire"
    WATER = "water"
    AIR = "air"
    EARTH = "earth"
    LIGHT = "light"
    DARKNESS = "darkness"
    NATURE = "nature"
    ARCANE = "arcane"


class GiftDTO(BaseModel):
    gift_id: str
    name_ru: str
    school: GiftSchool
    description: str
    role: str

    # Пока простая структура, как в исходном файле, но готовая к расширению
    abilities: list[str] = Field(default_factory=list)

    # Задел на будущее (прогрессия)
    abilities_progression: dict[int, list[str]] = Field(default_factory=dict)
