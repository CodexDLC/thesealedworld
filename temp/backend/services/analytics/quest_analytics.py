import asyncio
import csv
import os
from datetime import date
from typing import Any

from loguru import logger as log


class DynamicQuestAnalytics:
    def __init__(self):
        # Путь относительно корня проекта.
        # В реальном проекте лучше брать из конфига, но пока так.
        self.base_path = "data/analytics/quests"
        # Базовые поля, которые есть везде
        self.common_fields = ["timestamp", "session_id", "char_id", "seed", "step_count", "history"]

    async def log_result(self, quest_key: str, data: dict[str, Any], mapping_config: dict[str, str] = None) -> None:
        """
        quest_key: используется для названия файла (напр. 'awakening_rift')
        mapping_config: словарь {'поле_в_сессии': 'название_колонки_в_csv'}
        """
        # Ленивое создание директории
        if not os.path.exists(self.base_path):
            try:
                os.makedirs(self.base_path, exist_ok=True)
            except OSError as e:
                log.error(f"QuestAnalytics | status=failed reason='Could not create directory' error='{e}'")
                return

        filename = f"{self.base_path}/{quest_key}_{date.today()}.csv"

        # Если конфиг не передан, берем всё из data "как есть"
        row = self._prepare_row(data, mapping_config)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_csv_sync, filename, row)

    def _prepare_row(self, data: dict, mapping: dict | None) -> dict:
        # 1. Заполняем базовые поля
        row = {field: data.get(field, "") for field in self.common_fields}
        if isinstance(row["history"], list):
            row["history"] = ",".join(map(str, row["history"]))

        # 2. Добавляем кастомные поля из маппинга
        if mapping:
            for session_key, csv_column in mapping.items():
                # Если поле сложное (например, w_stats), мы его "разглаживаем" (flatten)
                source_value = data.get(session_key)

                if isinstance(source_value, dict):
                    # Превращаем {'strength': 10} в {'w_str': 10} через маппинг или префикс
                    for k, v in source_value.items():
                        # Используем первые 3 буквы ключа для краткости, если это статы
                        suffix = k[:3] if len(k) > 3 else k
                        row[f"{csv_column}_{suffix}"] = v
                else:
                    row[csv_column] = source_value
        return row

    def _write_csv_sync(self, filename: str, row: dict) -> None:
        file_exists = os.path.isfile(filename)
        # Извлекаем заголовки прямо из текущей строки
        fieldnames = list(row.keys())

        try:
            with open(filename, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except (OSError, csv.Error) as e:
            log.error(f"QuestAnalytics | error='{e}'")
        except Exception as e:  # noqa: BLE001
            log.error(f"QuestAnalytics | unexpected_error='{e}'")


# Глобальный экземпляр
quest_analytics = DynamicQuestAnalytics()
