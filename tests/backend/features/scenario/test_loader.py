import json
from unittest.mock import AsyncMock

import pytest

from src.backend.features.scenario.loaders.scenario_loader import ScenarioLoader


@pytest.mark.unit
class TestScenarioLoader:
    @pytest.fixture
    def importer(self):
        return AsyncMock()

    @pytest.fixture
    def loader(self, importer):
        return ScenarioLoader(importer)

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

        quest_key = await loader.load_from_file(file_path)

        assert quest_key == "test_quest"
        loader.importer.replace_quest.assert_awaited_once()
        master_data, nodes = loader.importer.replace_quest.await_args.args
        assert master_data["quest_key"] == "test_quest"
        assert [node["node_key"] for node in nodes] == ["start"]

    async def test_load_from_file_with_importer_without_cache(self, importer, tmp_path):
        importer.replace_quest.return_value = None
        loader = ScenarioLoader(importer)
        scenario_data = {
            "master": {"quest_key": "q", "start_node_id": "s", "status_bar_fields": []},
            "nodes": [],
        }
        file_path = tmp_path / "scenario.json"
        file_path.write_text(json.dumps(scenario_data))

        await loader.load_from_file(file_path)
        importer.replace_quest.assert_awaited_once()

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

        quest_key = await loader.load_from_file(fixture_dir)

        assert quest_key == "split_quest"
        inserted_nodes = loader.importer.replace_quest.await_args.args[1]
        assert [node["node_key"] for node in inserted_nodes] == ["start"]
        assert inserted_nodes[0]["node_type"] == "dialog"
        assert inserted_nodes[0]["phase"] == "arrival"
