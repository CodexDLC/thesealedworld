from collections.abc import Callable
from typing import Any

from google.genai import types
from loguru import logger as log

from src.backend.resources.llm_data.json_sheme import DUNGEON_JSON_SCHEMA_PROMPT
from src.backend.resources.llm_data.mode_preset import ChatMode

GeminiContents = str | list[types.ContentDict]
GeminiBuilder = Callable[..., tuple[GeminiContents, str]]


def build_simple_gemini(preset: dict, user_text: str, **kw: Any) -> tuple[GeminiContents, str]:
    """
    Универсальный сборщик промптов для простых текстовых задач Gemini.

    Формирует промпт, используя `system_instruction` из пресета и `user_text`
    в качестве основного содержимого.

    Args:
        preset: Пресет с настройками для модели, содержащий `system_instruction`.
        user_text: Основной текст для промпта (например, тема диалога).
        **kw: Дополнительные параметры (не используются в этом сборщике).

    Returns:
        Кортеж, содержащий:
        - contents: Содержимое промпта (строка).
        - system_instruction: Системная инструкция для модели.
    """
    # Логируем, какой именно режим обрабатывается (если есть имя в пресете)
    log.debug(f"GeminiBuilder | type=simple mode='{preset.get('name', 'generic')}'")
    system_instruction = preset["system_instruction"]
    contents = user_text
    return contents, system_instruction


def build_dungeon_gemini(
    preset: dict,
    user_text: str,  # Этот параметр игнорируется
    **kw: Any,
) -> tuple[GeminiContents, str]:
    """
    Специализированный сборщик промптов для генерации подземелий с Gemini.

    Формирует сложный промпт, комбинируя базовую инструкцию из пресета,
    тему подземелья из `**kw` и требования к JSON-схеме.

    Args:
        preset: Пресет для генерации подземелий, содержащий `system_instruction`.
        user_text: Игнорируется в этом сборщике.
        **kw: Дополнительные параметры, должен содержать `theme_prompt_from_db`
              (строка с темой подземелья).

    Returns:
        Кортеж, содержащий:
        - contents: Содержимое промпта (пустая строка, так как вся информация в system_instruction).
        - system_instruction: Финальная системная инструкция для модели.
    """
    log.debug("GeminiBuilder | type=dungeon_generator")
    theme_prompt_from_db = kw.get("theme_prompt_from_db")
    if not theme_prompt_from_db:
        log.warning("GeminiBuilder | status=warning reason='theme_prompt_from_db not provided'")
        theme_prompt_from_db = "Случайная тема на усмотрение ИИ."

    base_instruction = preset["system_instruction"]

    final_instruction = f"""
{base_instruction}

ЗАДАЧА:
{theme_prompt_from_db}

ТРЕБОВАНИЯ К ФОРМАТУ:
{DUNGEON_JSON_SCHEMA_PROMPT}
"""
    contents = ""
    log.debug(f"GeminiBuilder | instruction_formed theme='{theme_prompt_from_db[:50]}...'")
    return contents, final_instruction


# Реестр сборщиков промптов
BUILDERS_GEMINI: dict[ChatMode, GeminiBuilder] = {
    "dungeon_generator": build_dungeon_gemini,
    "item_description": build_simple_gemini,
    "npc_dialogue": build_simple_gemini,
    "batch_location_desc": build_simple_gemini,
    "clan_generation": build_simple_gemini,
}

log.debug(f"GeminiBuilder | status=registered count={len(BUILDERS_GEMINI)}")
