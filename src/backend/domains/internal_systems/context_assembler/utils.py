# apps/game_core/system/context_assembler/utils.py

# Список атрибутов (они всегда аддитивные, даже от предметов)
ATTRIBUTE_KEYS = {"strength", "agility", "endurance", "intelligence", "wisdom", "men", "perception", "charisma", "luck"}

# Список базовых статов экипировки (Урон, Броня), которые тоже аддитивные
BASE_EQUIPMENT_KEYS = {
    "physical_damage_min",
    "physical_damage_max",
    "magical_damage_min",
    "magical_damage_max",
    "damage_reduction_flat",
    "protection",
    # Локальная броня
    "armor_head",
    "armor_chest",
    "armor_arms",
    "armor_legs",
    "armor_feet",
}

# Список ключей, которые считаются МУЛЬТИПЛИКАТОРАМИ (*).
# Если в БД лежит число 0.5, оно превратится в "*1.5" (бонус +50% к базе).
# Если в БД лежит число -0.2, оно превратится в "*0.8" (штраф -20% от базы).
MULTIPLIER_KEYS = {
    # --- Шансы, которые скейлятся от статов ---
    "physical_crit_chance",
    "magical_crit_chance",
    "dodge_chance",
    # --- Мощность (Power/Mult) ---
    "physical_crit_power_float",
    "magical_crit_power_float",
    "damage_mult",
    "xp_multiplier",
    # --- Скорость ---
    "attack_speed",
    "movement_speed",
    "cast_speed",
    "crafting_speed",
    # --- Эффективность ---
    "resource_cost_reduction",  # 0.1 -> *0.9 (снижение затрат)
    "trade_discount",  # 0.1 -> *0.9 (скидка)
    "poison_efficiency",
    # --- Прочее ---
    "incoming_damage_reduction",  # Это точно мультипликатор (финальная срезка)
}


def format_value(key: str, value: int | float | str, source_type: str = "internal") -> str:
    """
    Адаптер для преобразования значений в Action-Based Strings.

    Args:
        key: Название характеристики.
        value: Значение (число или строка).
        source_type: 'internal' (Скиллы, Статы) или 'external' (Предметы, Баффы).
    """
    # 1. Zero-Transformation: Если уже строка, верим ей.
    if isinstance(value, str):
        return value

    # 2. Internal Source (Скиллы, Дары) -> Всегда Сложение (+)
    if source_type == "internal":
        return f"{value:+}"

    # 3. External Source (Предметы, Баффы) -> Умножение (*), кроме исключений
    if source_type == "external":
        # Исключение 1: Атрибуты от предметов (Кольцо силы) -> Сложение
        if key in ATTRIBUTE_KEYS:
            return f"{value:+}"

        # Исключение 2: Базовый урон оружия / Броня -> Сложение
        if key in BASE_EQUIPMENT_KEYS:
            return f"{value:+}"

        # Остальное (Крит, Скорость, Бонусы) -> Умножение
        # Эвристика: Если число маленькое (процент), делаем множитель.
        # Если число огромное (HP +100), оставляем плюс (пока не перепишем базу).
        if isinstance(value, (int, float)):
            if -1.0 < value < 5.0:  # Расширил до 500% (x5)
                final_val = 1.0 + value
                return f"*{final_val:.4f}"

            # Если значение > 5 (например +50 HP), считаем это плоским бонусом (Legacy)
            return f"{value:+}"

    # Fallback
    return f"{value:+}"
