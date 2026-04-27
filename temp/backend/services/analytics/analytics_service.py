import asyncio
import csv
import os
from datetime import date
from typing import Any

from loguru import logger as log


class AnalyticsService:
    """
    Сервис для сбора и записи аналитических данных о боевых сессиях.

    Результаты боев записываются в CSV-файлы асинхронно, чтобы не блокировать
    основной поток выполнения бота.
    """

    def __init__(self):
        """
        Инициализирует AnalyticsService и определяет заголовки для CSV-файлов.
        Создание директории происходит лениво при первой записи.
        """
        self.base_path = "data/analytics"
        self.fieldnames = [
            "timestamp",
            "date_iso",
            "session_id",
            "winner_team",
            "duration_sec",
            "total_rounds",
            "p1_id",
            "p1_name",
            "p1_team",
            "p1_hp_left",
            "p1_energy_left",
            "p1_dmg_dealt",
            "p1_dmg_taken",
            "p1_healing",
            "p1_blocks",
            "p1_dodges",
            "p1_crits",
            "p2_id",
            "p2_name",
            "p2_team",
            "p2_hp_left",
            "p2_energy_left",
            "p2_dmg_dealt",
            "p2_dmg_taken",
            "p2_healing",
            "p2_blocks",
            "p2_dodges",
            "p2_crits",
        ]
        log.debug(f"AnalyticsService | status=initialized base_path='{self.base_path}'")

    async def log_combat_result(self, combat_data: dict[str, Any]) -> None:
        """
        Асинхронно записывает результаты боевой сессии в CSV-файл.

        Использует `asyncio.run_in_executor` для выполнения синхронной
        операции записи в отдельном потоке, предотвращая блокировку
        основного цикла событий.

        Args:
            combat_data: Словарь, содержащий данные о боевой сессии.
                         Ключи словаря должны соответствовать `self.fieldnames`.
        """
        # Ленивое создание директории
        if not os.path.exists(self.base_path):
            try:
                os.makedirs(self.base_path, exist_ok=True)
            except OSError as e:
                log.error(f"AnalyticsService | status=failed reason='Could not create directory' error='{e}'")
                return

        filename = f"{self.base_path}/combats_{date.today()}.csv"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_csv_sync, filename, combat_data)
        log.info(
            f"AnalyticsService | event=combat_result_logged session_id='{combat_data.get('session_id')}' filename='{filename}'"
        )

    def _write_csv_sync(self, filename: str, data: dict[str, Any]) -> None:
        """
        Синхронная функция для записи данных в CSV-файл.

        Эта функция предназначена для выполнения в отдельном потоке.
        Если файл не существует, создаются заголовки.

        Args:
            filename: Полный путь к CSV-файлу.
            data: Словарь с данными для записи в одну строку CSV.
        """
        file_exists = os.path.isfile(filename)
        try:
            with open(filename, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                if not file_exists:
                    writer.writeheader()
                row = {k: data.get(k, "") for k in self.fieldnames}
                writer.writerow(row)
        except (OSError, csv.Error) as e:
            log.error(f"AnalyticsService | status=failed reason='Error writing CSV' filename='{filename}' error='{e}'")


analytics_service = AnalyticsService()
