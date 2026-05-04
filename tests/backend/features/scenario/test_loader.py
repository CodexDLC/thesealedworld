import json
from unittest.mock import AsyncMock, patch

import pytest

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
                "status_bar_fields": [],
            },
            "nodes": [
                {
                    "node_key": "start",
                    "quest_key": "test_quest",
                    "node_type": "event",
                    "text": "Hello",
                    "is_terminal": True,
                },
            ],
        }
        file_path = tmp_path / "scenario.json"
        file_path.write_text(json.dumps(scenario_data))

        with (
            patch(
                "src.backend.infrastructure.scenario.repositories.ScenarioRepository.upsert_master",
                new_callable=AsyncMock,
            ) as mock_upsert,
            patch(
                "src.backend.infrastructure.scenario.repositories.ScenarioRepository.delete_quest_nodes",
                new_callable=AsyncMock,
            ) as mock_delete,
            patch(
                "src.backend.infrastructure.scenario.repositories.ScenarioRepository.bulk_insert_nodes",
                new_callable=AsyncMock,
            ) as mock_bulk,
        ):
            quest_key = await loader.load_from_file(file_path)

            assert quest_key == "test_quest"
            mock_upsert.assert_called_once()
            mock_delete.assert_called_once_with("test_quest")
            mock_bulk.assert_called_once()
            loader.content.warm_up_cache.assert_called_once_with("test_quest")

    async def test_load_from_file_no_content_service(self, session, tmp_path):
        loader = ScenarioLoader(session, content=None)
        scenario_data = {
            "master": {"quest_key": "q", "start_node_id": "s", "status_bar_fields": []},
            "nodes": [],
        }
        file_path = tmp_path / "scenario.json"
        file_path.write_text(json.dumps(scenario_data))

        with (
            patch(
                "src.backend.infrastructure.scenario.repositories.ScenarioRepository.upsert_master",
                new_callable=AsyncMock,
            ),
            patch(
                "src.backend.infrastructure.scenario.repositories.ScenarioRepository.delete_quest_nodes",
                new_callable=AsyncMock,
            ),
            patch(
                "src.backend.infrastructure.scenario.repositories.ScenarioRepository.bulk_insert_nodes",
                new_callable=AsyncMock,
            ),
        ):
            await loader.load_from_file(file_path)
            # Should not crash without content service

    async def test_load_from_directory_prefers_nodes_folder(self, loader, tmp_path):
        fixture_dir = tmp_path / "split_quest"
        fixture_dir.mkdir()
        nodes_dir = fixture_dir / "nodes"
        nodes_dir.mkdir()

        (fixture_dir / "master.json").write_text(
            json.dumps(
                {
                    "quest_key": "split_quest",
                    "start_node_id": "start",
                    "status_bar_fields": [],
                },
            ),
            encoding="utf-8",
        )
        (fixture_dir / "nodes_part_1.json").write_text(
            json.dumps(
                [
                    {
                        "node_key": "legacy_node",
                        "node_type": "event",
                        "text": "This file should be ignored.",
                    },
                ],
            ),
            encoding="utf-8",
        )
        (nodes_dir / "00_start.json").write_text(
            json.dumps(
                [
                    {
                        "node_key": "start",
                        "node_type": "dialog",
                        "phase": "arrival",
                        "speaker": "overseer",
                        "text": "New layout wins.",
                    },
                ],
            ),
            encoding="utf-8",
        )

        with (
            patch(
                "src.backend.infrastructure.scenario.repositories.ScenarioRepository.upsert_master",
                new_callable=AsyncMock,
            ),
            patch(
                "src.backend.infrastructure.scenario.repositories.ScenarioRepository.delete_quest_nodes",
                new_callable=AsyncMock,
            ),
            patch(
                "src.backend.infrastructure.scenario.repositories.ScenarioRepository.bulk_insert_nodes",
                new_callable=AsyncMock,
            ) as mock_bulk,
        ):
            quest_key = await loader.load_from_file(fixture_dir)

        assert quest_key == "split_quest"
        inserted_nodes = mock_bulk.call_args.args[0]
        assert [node["node_key"] for node in inserted_nodes] == ["start"]
        assert inserted_nodes[0]["node_type"] == "dialog"
        assert inserted_nodes[0]["phase"] == "arrival"
