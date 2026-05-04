# backend/domains/user_features/scenario/resources/loaders/scenario_loader.py
import json
import os
from pathlib import Path
from typing import Any

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.postgres.repositories.scenario_repository import ScenarioRepositoryORM


class ScenarioLoader:
    """
    Утилита для загрузки сценариев из JSON-файлов в базу данных.
    """

    def __init__(self, session: AsyncSession):
        self.repo = ScenarioRepositoryORM(session)

        # Вычисляем абсолютный путь к папке с JSON относительно этого файла
        # Файл лежит в: .../scenario/resources/loaders/scenario_loader.py
        # JSON лежат в: .../scenario/resources/json/
        current_dir = Path(__file__).parent
        self.scenarios_dir = current_dir.parent / "json"

    async def load_all_scenarios(self):
        """
        Сканирует директорию сценариев и загружает каждый найденный JSON.
        """
        if not self.scenarios_dir.exists():
            log.error(f"ScenarioLoader | Directory not found: {self.scenarios_dir}")
            return

        log.info(f"ScenarioLoader | Scanning directory: {self.scenarios_dir}")

        files = [f for f in os.listdir(self.scenarios_dir) if f.endswith(".json")]
        if not files:
            log.warning("ScenarioLoader | No JSON files found.")
            return

        for filename in files:
            file_path = self.scenarios_dir / filename
            await self.load_scenario_from_file(file_path)

    async def load_scenario_from_file(self, file_path: Path):
        """
        Читает файл, валидирует структуру и сохраняет в БД.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            if not self._validate_structure(data):
                log.error(f"ScenarioLoader | Invalid structure in file: {file_path.name}")
                return

            master_data = data["master"]
            quest_key = master_data["quest_key"]
            log.info(f"ScenarioLoader | Loading quest '{quest_key}' from {file_path.name}...")

            # --- Адаптация данных под модель БД ---
            if "analytics_config" in master_data:
                if "config" not in master_data:
                    master_data["config"] = {}
                master_data["config"]["analytics"] = master_data.pop("analytics_config")

            # 1. Сохраняем Master
            await self.repo.upsert_master(master_data)

            # 2. Очищаем старые ноды этого квеста
            await self.repo.delete_quest_nodes(quest_key)

            # 3. Подготовка данных для Bulk Insert
            nodes_to_insert = []
            for node in data["nodes"]:
                node["quest_key"] = quest_key

                # АВТО-ЗАПОЛНЕНИЕ ТЕКСТА ДЛЯ ТЕХНИЧЕСКИХ НОД
                if "text_content" not in node or node["text_content"] is None:
                    node["text_content"] = "[System: Logic Processing...]"

                nodes_to_insert.append(node)

            # 4. Массовая вставка
            if nodes_to_insert:
                await self.repo.bulk_insert_nodes(nodes_to_insert)

            # Коммитим транзакцию
            await self.repo.session.commit()

            log.success(f"ScenarioLoader | Quest '{quest_key}' loaded successfully. Nodes: {len(nodes_to_insert)}")

        except Exception as e:  # noqa: BLE001
            log.exception(f"ScenarioLoader | Failed to load {file_path.name}: {e}")
            await self.repo.session.rollback()

    def _validate_structure(self, data: dict[str, Any]) -> bool:
        """Проверяет наличие обязательных ключей."""
        if "master" not in data or "nodes" not in data:
            return False
        if "quest_key" not in data["master"]:
            return False
        return isinstance(data["nodes"], list)
