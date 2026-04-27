import hashlib

from src.backend.resources.game_data.monsters.spawn_config import MUTATION_TAGS_WHITELIST


def normalize_tags(raw_tags: list[str]) -> list[str]:
    """
    Фильтрует и сортирует теги.
    1. Оставляет только те, которые влияют на мутации (whitelist).
    2. Сортирует по алфавиту, чтобы ['ice', 'ruins'] == ['ruins', 'ice'].
    """
    if not raw_tags:
        return []

    # Пересечение с вайтлистом, чтобы мусорные теги не меняли хеш
    filtered = set(raw_tags) & MUTATION_TAGS_WHITELIST
    return sorted(list(filtered))


def compute_context_hash(tier: int, biome_id: str, normalized_tags: list[str]) -> str:
    """
    Генерирует хеш ОКРУЖЕНИЯ (Shared Context).

    Если два игрока зашли в разные зоны (Zone A, Zone B), но у обеих зон:
    - Tier 1
    - Biome Forest
    - Tags [Rain, Night]
    -> Хеш будет ОДИНАКОВЫЙ. Это позволяет переиспользовать клан.
    """
    tags_str = "_".join(normalized_tags)
    # Формат: "forest_t1_night_rain"
    raw_key = f"{biome_id}_t{tier}_{tags_str}"

    # MD5 для компактности и предсказуемости
    return hashlib.md5(raw_key.encode()).hexdigest()


def compute_unique_clan_hash(family_id: str, context_hash: str) -> str:
    """
    Генерирует уникальный ID конкретного клана в конкретных условиях.
    Используется для проверки exists() в БД.
    """
    raw_key = f"{family_id}_{context_hash}"
    return hashlib.md5(raw_key.encode()).hexdigest()
