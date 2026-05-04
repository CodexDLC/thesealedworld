from enum import Enum

from pydantic import BaseModel, Field


class SkillCategory(str, Enum):
    COMBAT = "combat"
    NON_COMBAT = "non_combat"


class SkillGroup(str, Enum):
    # Combat Groups
    WEAPON_MASTERY = "weapon_mastery"
    TACTICAL = "tactical"
    ARMOR = "armor"
    COMBAT_SUPPORT = "combat_support"

    # Non-Combat Groups
    GATHERING = "gathering"
    CRAFTING = "crafting"
    TRADE = "trade"  # Новая группа
    SOCIAL = "social"  # Лидерство и кланы
    SURVIVAL = "survival"
    OTHER = "other"


class SkillDTO(BaseModel):
    """
    DTO для определения навыка в библиотеке (Static Data).
    Не содержит прогресса конкретного игрока.
    """

    skill_key: str = Field(..., description="Уникальный ключ навыка (например, 'mining')")
    name_en: str = Field(..., description="Название на английском")
    name_ru: str = Field(..., description="Название на русском")

    category: SkillCategory = Field(default=SkillCategory.NON_COMBAT, description="Категория навыка (Боевой/Мирный)")
    group: SkillGroup = Field(
        default=SkillGroup.OTHER, description="Подгруппа навыка (например, Weapon Mastery, Survival)"
    )

    # Параметры прогрессии (Math Spec)
    stat_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Веса характеристик для расчета Base Power (Тяги). Например: {'strength': 2.0, 'agility': 1.0}",
    )
    rate_mod: float = Field(default=1.0, description="Модификатор скорости (Rate Mod). Множитель для GLOBAL_BASE_RATE.")
    wall_mod: float = Field(
        default=1.0,
        description="Модификатор стены (Wall Mod). Множитель для GLOBAL_BASE_WALL. Определяет сложность достижения капа.",
    )

    description: str | None = Field(None, description="Техническое описание или описание для игрока")
