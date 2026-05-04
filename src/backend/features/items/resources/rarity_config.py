from typing import TypedDict

from src.backend.features.items.dto.enums import ItemRarity


class RarityMeta(TypedDict):
    enum_key: ItemRarity  # Ссылка на Enum из DTO
    name_ru: str  # Русское название для UI
    color_hex: str  # Цвет для embed/текста
    default_mult: float  # Базовый множитель (резервный)
    slots_capacity: int  # Базовая вместимость (резерв)


# Маппинг: Tier (int) -> Settings
RARITY_CONFIG: dict[int, RarityMeta] = {
    0: {
        "enum_key": ItemRarity.COMMON,
        "name_ru": "Обычный",
        "color_hex": "#FFFFFF",  # Белый
        "default_mult": 1.0,
        "slots_capacity": 0,
    },
    1: {
        "enum_key": ItemRarity.UNCOMMON,
        "name_ru": "Необычный",
        "color_hex": "#1EFF00",  # Зеленый
        "default_mult": 1.2,
        "slots_capacity": 1,
    },
    2: {
        "enum_key": ItemRarity.RARE,
        "name_ru": "Редкий",
        "color_hex": "#0070DD",  # Синий
        "default_mult": 1.5,
        "slots_capacity": 2,
    },
    3: {
        "enum_key": ItemRarity.EPIC,
        "name_ru": "Эпический",
        "color_hex": "#A335EE",  # Фиолетовый
        "default_mult": 2.2,
        "slots_capacity": 3,
    },
    4: {
        "enum_key": ItemRarity.LEGENDARY,
        "name_ru": "Легендарный",
        "color_hex": "#FF8000",  # Оранжевый
        "default_mult": 3.5,
        "slots_capacity": 4,
    },
    5: {
        "enum_key": ItemRarity.MYTHIC,
        "name_ru": "Мифический",
        "color_hex": "#CC0000",  # Красный
        "default_mult": 5.0,
        "slots_capacity": 4,
    },
    6: {
        "enum_key": ItemRarity.EXOTIC,
        "name_ru": "Экзотик",
        "color_hex": "#FF00FF",  # Розовый/Маджента
        "default_mult": 7.5,
        "slots_capacity": 4,
    },
    7: {
        "enum_key": ItemRarity.ABSOLUTE,
        "name_ru": "Абсолют",
        "color_hex": "#000000",  # Черный (или глубокий золотой)
        "default_mult": 10.0,
        "slots_capacity": 5,
    },
}


def get_rarity_by_tier(tier: int) -> RarityMeta:
    """Безопасное получение конфига. Если тир > 7, вернет 7."""
    safe_tier = max(0, min(tier, 7))
    return RARITY_CONFIG[safe_tier]
