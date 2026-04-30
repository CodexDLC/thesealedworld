import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from src.backend.features.scenario.loaders.scenario_loader import ScenarioLoader

@pytest.mark.unit
class TestScenarioLoader:
    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def content(self):
        return AsyncMock()

    @pytest.fixture
    def loader(self, session, content):
        return ScenarioLoader(session, content)

    async def test_load_from_file(self, loader, tmp_path):
        # Create a dummy scenario file
        scenario_data = {
            "master": {
                "quest_key": "test_quest",
                "start_node_id": "start",
                "status_bar_fields": []
            },
            "nodes": [
                {"node_key": "start", "quest_key": "test_quest", "text_content": "Hello", "is_terminal": True}
            ]
        }
        file_path = tmp_path / "scenario.json"
        file_path.write_text(json.dumps(scenario_data))

        with patch("src.backend.infrastructure.db.scenario.repositories.ScenarioRepository.upsert_master", new_callable=AsyncMock) as mock_upsert, \
             patch("src.backend.infrastructure.db.scenario.repositories.ScenarioRepository.delete_quest_nodes", new_callable=AsyncMock) as mock_delete, \
             patch("src.backend.infrastructure.db.scenario.repositories.ScenarioRepository.bulk_insert_nodes", new_callable=AsyncMock) as mock_bulk:

            quest_key = await loader.load_from_file(file_path)

            assert quest_key == "test_quest"
            mock_upsert.assert_called_once()
            mock_delete.assert_called_once_with("test_quest")
            mock_bulk.assert_called_once()
            loader.content.invalidate.assert_called_once_with("test_quest")

    async def test_load_from_file_no_content_service(self, session, tmp_path):
        loader = ScenarioLoader(session, content=None)
        scenario_data = {
            "master": {"quest_key": "q", "start_node_id": "s", "status_bar_fields": []},
            "nodes": []
        }
        file_path = tmp_path / "scenario.json"
        file_path.write_text(json.dumps(scenario_data))

        with patch("src.backend.infrastructure.db.scenario.repositories.ScenarioRepository.upsert_master", new_callable=AsyncMock), \
             patch("src.backend.infrastructure.db.scenario.repositories.ScenarioRepository.delete_quest_nodes", new_callable=AsyncMock), \
             patch("src.backend.infrastructure.db.scenario.repositories.ScenarioRepository.bulk_insert_nodes", new_callable=AsyncMock):

            await loader.load_from_file(file_path)
            # Should not crash without content service
