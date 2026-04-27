import re

from loguru import logger as log

from src.backend.resources.profanity_list import FORBIDDEN_WORDS

# Константы выносим в начало для удобной настройки
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 16
# Разрешаем буквы (RU/EN), цифры и нижнее подчеркивание
NAME_PATTERN = re.compile(r"^[a-zA-Zа-яА-Я0-9_]+$")


def validate_character_name(name: str) -> tuple[bool, str | None]:
    """
    Универсальный валидатор имени персонажа.
    Проверяет длину, символы и наличие запрещенных слов (регистронезависимо).
    """
    if not name:
        return False, "⚠️ Имя не может быть пустым."

    name = name.strip()
    name_len = len(name)

    # 1. Проверка длины
    if not (MIN_NAME_LENGTH <= name_len <= MAX_NAME_LENGTH):
        log.debug(f"Validator | Failed length check: {name_len}")
        return False, f"⚠️ Длина имени должна быть от {MIN_NAME_LENGTH} до {MAX_NAME_LENGTH} символов."

    # 2. Проверка паттерна (символы)
    if not NAME_PATTERN.match(name):
        log.debug(f"Validator | Invalid characters in: {name}")
        return False, "⚠️ Имя содержит недопустимые символы. Разрешены только буквы, цифры и '_'."

    # 3. Максимальная проверка на мат/запрещенку (Case-insensitive)
    name_lower = name.lower()

    # Сначала проверяем полное совпадение
    if name_lower in FORBIDDEN_WORDS:
        log.debug(f"Validator | Forbidden word (exact): {name_lower}")
        return False, "⚠️ Это имя зарезервировано или запрещено."

    # Затем проверяем вхождение запрещенных слов (частичное совпадение)
    for forbidden in FORBIDDEN_WORDS:
        if forbidden in name_lower:
            log.debug(f"Validator | Forbidden substring: '{forbidden}' in '{name_lower}'")
            return False, "⚠️ Имя содержит недопустимую комбинацию символов."

    return True, None
