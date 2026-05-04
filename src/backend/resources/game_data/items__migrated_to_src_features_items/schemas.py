from pydantic import BaseModel, Field


class ResourceDTO(BaseModel):
    """DTO для сырьевых ресурсов (Raw Resources)."""

    id: str
    name_ru: str
    base_price: int
    narrative_description: str


class MaterialDTO(BaseModel):
    """DTO для обработанных материалов (Materials)."""

    id: str
    name_ru: str
    tier_mult: float
    slots: int
    narrative_tags: list[str] = Field(default_factory=list)
    narrative_description: str | None = None  # Добавлено для унификации


class BaseItemDTO(BaseModel):
    """DTO для базовых предметов (Base Items / Болванок)."""

    id: str
    name_ru: str
    slot: str
    type: str | None = None  # weapon, armor, accessory

    # Характеристики
    base_power: int
    base_durability: int
    damage_spread: float = 0.1

    # Типы урона/защиты
    damage_type: str | None = None
    defense_type: str | None = None

    # Крафт
    allowed_materials: list[str] = Field(default_factory=list)
    extra_slots: list[str] = Field(default_factory=list)

    # Бонусы
    implicit_bonuses: dict[str, float] = Field(default_factory=dict)

    # Триггеры (ссылки на TriggerRegistry)
    triggers: list[str] = Field(default_factory=list)

    narrative_tags: list[str] = Field(default_factory=list)
