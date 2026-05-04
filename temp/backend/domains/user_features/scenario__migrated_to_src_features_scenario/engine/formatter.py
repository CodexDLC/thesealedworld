# backend/domains/user_features/scenario/engine/formatter.py
import re
from typing import Any

from src.shared.schemas.scenario import (
    ScenarioButtonDTO,
    ScenarioPayloadDTO,
)


class ScenarioFormatter:
    """
    Саппорт-класс для подготовки данных для API.
    Реализует парсинг тегов в тексте и сборку DTO ответа.
    """

    def __init__(self):
        # Паттерн для поиска тегов типа [#stats:str] или [#loot_queue.0]
        # Теперь поддерживает точки и цифры в имени переменной
        # Исправлено: убрано избыточное экранирование точки внутри []
        self.tag_pattern = re.compile(r"\[#(?:stats:)?([\w.]+)\]")

    # --- 1. Text Processing (Парсинг переменных в тексте) ---

    def format_text(self, text: str, context: dict[str, Any]) -> str:
        """
        Заменяет плейсхолдеры в тексте на реальные значения из контекста.
        Поддерживает вложенный доступ через точку (например, loot_queue.0).
        """
        if not text:
            return ""

        def replace_tag(match):
            full_key = match.group(1)

            # Попытка разрешить ключ с точками (вложенность/индексы)
            keys = full_key.split(".")
            value: Any = context

            try:
                for k in keys:
                    if isinstance(value, dict):
                        value = value.get(k)
                    elif isinstance(value, list):
                        # Если ключ - число, пробуем индекс
                        if k.isdigit():
                            idx = int(k)
                            if 0 <= idx < len(value):
                                value = value[idx]
                            else:
                                return f"Unknown:{full_key}"
                        else:
                            return f"Unknown:{full_key}"
                    else:
                        return f"Unknown:{full_key}"

                    if value is None:
                        return f"Unknown:{full_key}"

                return str(value)
            except (KeyError, IndexError, ValueError, AttributeError):
                return f"Unknown:{full_key}"

        return self.tag_pattern.sub(replace_tag, text)

    # --- 2. Status Bar Builder (Подготовка данных для статус-бара) ---

    def build_status_bar_data(self, master_config: dict[str, Any], context: dict[str, Any]) -> list[str]:
        """
        Формирует список строк для статус-бара.
        Пример: ["❤️ HP: 100", "💰 Золото: 50"]
        """
        fields = master_config.get("status_bar_fields", [])
        if not fields:
            return []

        status_parts = []
        for field in fields:
            label = field.get("label", "")
            key = field.get("key")
            val = context.get(key, "??")
            status_parts.append(f"{label} {val}")

        return status_parts

    # --- 3. DTO Builder (Сборка финального пакета) ---

    def build_dto(
        self,
        node_data: dict[str, Any],
        available_actions: list[dict[str, Any]],
        context: dict[str, Any],
        master_config: dict[str, Any],
    ) -> ScenarioPayloadDTO:
        """
        Собирает итоговый DTO (Payload).
        """
        # Подготавливаем художественный текст
        raw_text = node_data.get("text_content", "")
        formatted_text = self.format_text(raw_text, context)

        # Форматируем лейблы кнопок (там тоже могут быть переменные)
        formatted_actions = []
        for action in available_actions:
            action_copy = action.copy()
            action_copy["label"] = self.format_text(action["label"], context)
            formatted_actions.append(action_copy)

        # Собираем данные для статус-бара
        status_bar_lines = self.build_status_bar_data(master_config, context)

        # Формируем список кнопок
        buttons_dto = [
            ScenarioButtonDTO(label=action["label"], action_id=action["action_id"]) for action in formatted_actions
        ]

        # Формируем Payload
        return ScenarioPayloadDTO(
            node_key=node_data.get("node_key", "unknown"),
            text=formatted_text,
            status_bar=status_bar_lines,
            buttons=buttons_dto,
            is_terminal=node_data.get("is_terminal", False),
        )
