import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select
from src.backend.infrastructure.db.scenario.repositories.scenario_repository import ScenarioRepository
from src.backend.infrastructure.db.scenario.models import ScenarioMaster, ScenarioNode, CharacterQuestState

@pytest.mark.unit
class TestScenarioRepository:
    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return ScenarioRepository(session)

    async def test_get_master_found(self, repo, session):
        mock_master = MagicMock()
        mock_master.quest_key = "q1"
        mock_master.start_node_id = "n1"
        mock_master.master_data = {"foo": "bar"}
        mock_master.status_bar_fields = []
        mock_master.config = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_master
        session.execute.return_value = mock_result

        result = await repo.get_master("q1")
        assert result["quest_key"] == "q1"
        assert result["foo"] == "bar"

    async def test_get_master_not_found(self, repo, session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        result = await repo.get_master("unknown")
        assert result is None

    async def test_upsert_master(self, repo, session):
        master_data = {"quest_key": "q1", "display_name": "Quest 1", "start_node_id": "n1", "foo": "bar"}
        await repo.upsert_master(master_data)
        session.execute.assert_called_once()

    async def test_get_node_found(self, repo, session):
        mock_node = MagicMock()
        mock_node.quest_key = "q1"
        mock_node.node_key = "n1"
        mock_node.node_data = {"text": "Hello"}
        mock_node.tags = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_node
        session.execute.return_value = mock_result

        result = await repo.get_node("q1", "n1")
        assert result["node_key"] == "n1"
        assert result["text"] == "Hello"

    async def test_get_nodes_by_pool(self, repo, session):
        mock_node = MagicMock()
        mock_node.quest_key = "q1"
        mock_node.node_key = "n1"
        mock_node.node_data = {}
        mock_node.tags = ["tag1"]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_node]
        session.execute.return_value = mock_result

        result = await repo.get_nodes_by_pool("q1", "tag1")
        assert len(result) == 1
        assert result[0]["node_key"] == "n1"

    async def test_get_all_quest_nodes(self, repo, session):
        mock_node = MagicMock()
        mock_node.quest_key = "q1"
        mock_node.node_key = "n1"
        mock_node.node_data = {}
        mock_node.tags = []

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_node]
        session.execute.return_value = mock_result

        result = await repo.get_all_quest_nodes("q1")
        assert len(result) == 1

    async def test_bulk_insert_nodes(self, repo, session):
        nodes = [{"quest_key": "q1", "node_key": "n1"}, {"quest_key": "q1", "node_key": "n2"}]
        await repo.bulk_insert_nodes(nodes)
        session.execute.assert_called_once()

    async def test_bulk_insert_nodes_empty(self, repo, session):
        await repo.bulk_insert_nodes([])
        session.execute.assert_not_called()

    async def test_delete_quest_nodes(self, repo, session):
        await repo.delete_quest_nodes("q1")
        session.execute.assert_called_once()

    async def test_get_active_state_found(self, repo, session):
        mock_state = MagicMock()
        mock_state.character_id = 1
        mock_state.quest_key = "q1"
        mock_state.node_key = "n1"
        mock_state.context = {}
        mock_state.session_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        session.execute.return_value = mock_result

        result = await repo.get_active_state(1)
        assert result["character_id"] == 1
        assert result["quest_key"] == "q1"

    async def test_get_active_state_not_found(self, repo, session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        result = await repo.get_active_state(1)
        assert result is None

    async def test_upsert_state(self, repo, session):
        await repo.upsert_state(1, "q1", "n1", {}, uuid.uuid4())
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    async def test_delete_state(self, repo, session):
        await repo.delete_state(1)
        session.execute.assert_called_once()
        session.commit.assert_called_once()
