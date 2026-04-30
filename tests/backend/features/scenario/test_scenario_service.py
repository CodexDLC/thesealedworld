import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.backend.features.scenario.services.scenario_service import (
    ScenarioService, ScenarioNotFoundError, ScenarioSessionNotFoundError, InvalidActionError
)
from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.shared.enums import CoreDomain

@pytest.mark.unit
class TestScenarioService:
    @pytest.fixture
    def mocks(self):
        return {
            "content": MagicMock(),
            "sessions": MagicMock(),
            "character_sessions": MagicMock(),
            "repo": MagicMock(),
            "evaluator": MagicMock(),
            "director": MagicMock(),
            "formatter": MagicMock(),
            "events": MagicMock(),
            "redis": MagicMock(),
        }

    @pytest.fixture
    def service(self, mocks):
        return ScenarioService(**mocks)

    async def test_initialize_success(self, service, mocks):
        import uuid
        char_id = 1
        quest_key = "q1"
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})

        mock_handler = MagicMock()
        context = ScenarioContextDTO(
            quest_key=quest_key,
            current_node_key="n1",
            scenario_session_id=uuid.uuid4()
        )
        mock_handler.on_initialize = AsyncMock(return_value=context)

        with patch("src.backend.features.scenario.services.scenario_service.get_handler", return_value=mock_handler):
            mocks["sessions"].create = AsyncMock()
            mocks["character_sessions"].transition_state = AsyncMock()
            mocks["character_sessions"].set_scenario_session = AsyncMock()
            mocks["repo"].upsert_state = AsyncMock()
            mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
            mocks["formatter"].render_payload.return_value = {"rendered": True}
            mocks["events"].publish = AsyncMock()

            result = await service.initialize(char_id, quest_key)

            assert result == {"rendered": True}
            mocks["sessions"].create.assert_called_once()
            mocks["repo"].upsert_state.assert_called_once()

    async def test_initialize_not_found(self, service, mocks):
        mocks["content"].get_master = AsyncMock(return_value=None)
        with pytest.raises(ScenarioNotFoundError):
            await service.initialize(1, "unknown")

    async def test_resume_success(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})
        mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
        mocks["formatter"].render_payload.return_value = {"rendered": True}
        mocks["events"].publish = AsyncMock()

        result = await service.resume(char_id)
        assert result == {"rendered": True}

    async def test_resume_repair(self, service, mocks):
        import uuid
        char_id = 1
        mocks["sessions"].get = AsyncMock(return_value=None)
        mocks["repo"].get_active_state = AsyncMock(return_value={"context": {"quest_key": "q1", "current_node_key": "n1", "scenario_session_id": str(uuid.uuid4())}})
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})
        mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
        mocks["sessions"].create = AsyncMock()
        mocks["character_sessions"].set_scenario_session = AsyncMock()
        mocks["events"].publish = AsyncMock()

        await service.resume(char_id)
        mocks["sessions"].create.assert_called_once()

    async def test_resume_not_found(self, service, mocks):
        mocks["sessions"].get = AsyncMock(return_value=None)
        mocks["repo"].get_active_state = AsyncMock(return_value=None)
        mocks["events"].publish = AsyncMock()
        with pytest.raises(ScenarioSessionNotFoundError):
            await service.resume(1)

    async def test_step_success(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"a1": {"type": "move"}}})

        mock_resolved = MagicMock()
        mock_resolved.node = {"node_key": "n2"}
        mock_resolved.context = {}
        mocks["director"].resolve_next_node = AsyncMock(return_value=mock_resolved)

        mocks["sessions"].patch = AsyncMock()
        mocks["repo"].upsert_state = AsyncMock()
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})
        mocks["events"].publish = AsyncMock()

        await service.step(char_id, "a1")
        assert context.current_node_key == "n2"
        mocks["sessions"].patch.assert_called_once()
        mocks["repo"].upsert_state.assert_called_once()

    async def test_step_terminal(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"a1": {"type": "move"}}})

        mock_resolved = MagicMock()
        mock_resolved.node = {"node_key": "end", "is_terminal": True}
        mock_resolved.context = {}
        mocks["director"].resolve_next_node = AsyncMock(return_value=mock_resolved)

        mocks["sessions"].patch = AsyncMock()
        mocks["repo"].upsert_state = AsyncMock()
        mocks["events"].publish = AsyncMock()

        # Mock finalize
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})
        mock_handler = MagicMock()
        mock_handler.on_finalize = AsyncMock()
        with patch("src.backend.features.scenario.services.scenario_service.get_handler", return_value=mock_handler):
            mocks["character_sessions"].transition_state = AsyncMock()
            mocks["character_sessions"].clear_scenario_session = AsyncMock()
            mocks["sessions"].delete = AsyncMock()
            mocks["repo"].delete_state = AsyncMock()

            await service.step(char_id, "a1")
            mocks["sessions"].delete.assert_called_with(char_id)

    async def test_initialize_auto_chain(self, service, mocks):
        import uuid
        char_id = 1
        quest_key = "q1"
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})

        mock_handler = MagicMock()
        context = ScenarioContextDTO(
            quest_key=quest_key,
            current_node_key="n1",
            scenario_session_id=uuid.uuid4()
        )
        mock_handler.on_initialize = AsyncMock(return_value=context)

        with patch("src.backend.features.scenario.services.scenario_service.get_handler", return_value=mock_handler):
            mocks["sessions"].create = AsyncMock()
            mocks["character_sessions"].transition_state = AsyncMock()
            mocks["character_sessions"].set_scenario_session = AsyncMock()
            mocks["repo"].upsert_state = AsyncMock()
            mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"auto": {}}})

            mock_resolved = MagicMock()
            mock_resolved.node = {"node_key": "n2"}
            mock_resolved.context = {"foo": "bar"}
            mocks["director"].execute_auto_chain = AsyncMock(return_value=mock_resolved)

            mocks["sessions"].patch = AsyncMock()
            mocks["formatter"].render_payload.return_value = {"rendered": True}
            mocks["events"].publish = AsyncMock()

            await service.initialize(char_id, quest_key)

            assert context.current_node_key == "n2"
            mocks["director"].execute_auto_chain.assert_called_once()

    async def test_step_terminal(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"a1": {"type": "move"}}})

        mock_resolved = MagicMock()
        mock_resolved.node = {"node_key": "end", "is_terminal": True}
        mock_resolved.context = {}
        mocks["director"].resolve_next_node = AsyncMock(return_value=mock_resolved)

        mocks["sessions"].patch = AsyncMock()
        mocks["repo"].upsert_state = AsyncMock()
        mocks["events"].publish = AsyncMock()

        # Mock finalize
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})
        mock_handler = MagicMock()
        mock_result = MagicMock()
        mock_result.rewards.items = []
        mock_result.rewards.skills = []
        mock_result.rewards.attribute_bonuses = None
        mock_handler.on_finalize = AsyncMock(return_value=mock_result)

        with patch("src.backend.features.scenario.services.scenario_service.get_handler", return_value=mock_handler):
            mocks["character_sessions"].transition_state = AsyncMock()
            mocks["character_sessions"].clear_scenario_session = AsyncMock()
            mocks["sessions"].delete = AsyncMock()
            mocks["repo"].delete_state = AsyncMock()

            await service.step(char_id, "a1")
            mocks["sessions"].delete.assert_called_with(char_id)

    async def test_initialize_state_transition_error(self, service, mocks):
        import uuid
        from src.backend.infrastructure.redis.character_session_manager import StateTransitionError
        char_id = 1
        quest_key = "q1"
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})

        mock_handler = MagicMock()
        context = ScenarioContextDTO(quest_key=quest_key, current_node_key="n1", scenario_session_id=uuid.uuid4())
        mock_handler.on_initialize = AsyncMock(return_value=context)

        with patch("src.backend.features.scenario.services.scenario_service.get_handler", return_value=mock_handler):
            mocks["sessions"].create = AsyncMock()
            mocks["character_sessions"].transition_state = AsyncMock(side_effect=StateTransitionError("fail"))
            mocks["character_sessions"].set_scenario_session = AsyncMock()
            mocks["repo"].upsert_state = AsyncMock()
            mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
            mocks["formatter"].render_payload.return_value = {}
            mocks["events"].publish = AsyncMock()

            # Should not raise
            await service.initialize(char_id, quest_key)

    async def test_step_invalid_condition(self, service, mocks):
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"a1": {"condition": "fail"}}})
        mocks["evaluator"].check_condition.return_value = False
        with pytest.raises(InvalidActionError):
            await service.step(1, "a1")

    async def test_step_finish_quest(self, service, mocks):
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"a1": {"type": "finish_quest"}}})

        # Mock finalize
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})
        mock_handler = MagicMock()
        mock_result = MagicMock()
        mock_result.rewards.items = []
        mock_result.rewards.skills = []
        mock_result.rewards.attribute_bonuses = None
        mock_handler.on_finalize = AsyncMock(return_value=mock_result)

        with patch("src.backend.features.scenario.services.scenario_service.get_handler", return_value=mock_handler):
            mocks["character_sessions"].transition_state = AsyncMock()
            mocks["character_sessions"].clear_scenario_session = AsyncMock()
            mocks["sessions"].delete = AsyncMock()
            mocks["repo"].delete_state = AsyncMock()
            mocks["events"].publish = AsyncMock()

            await service.step(1, "a1")
            mocks["sessions"].delete.assert_called_once()

    async def test_resume_auto_chain(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})
        mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"auto": {}}})

        mock_resolved = MagicMock()
        mock_resolved.node = {"node_key": "n2"}
        mock_resolved.context = {"foo": "bar"}
        mocks["director"].execute_auto_chain = AsyncMock(return_value=mock_resolved)

        mocks["sessions"].patch = AsyncMock()
        mocks["formatter"].render_payload.return_value = {}
        mocks["events"].publish = AsyncMock()

        await service.resume(char_id)
        assert context.current_node_key == "n2"
        mocks["director"].execute_auto_chain.assert_called_once()

    async def test_resume_master_not_found(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="missing", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_master = AsyncMock(return_value=None)
        with pytest.raises(ScenarioNotFoundError):
            await service.resume(char_id)

    async def test_step_session_not_found(self, service, mocks):
        mocks["sessions"].get = AsyncMock(return_value=None)
        with pytest.raises(ScenarioSessionNotFoundError):
            await service.step(1, "a1")

    async def test_finalize_session_not_found(self, service, mocks):
        mocks["sessions"].get = AsyncMock(return_value=None)
        with pytest.raises(ScenarioSessionNotFoundError):
            await service.finalize(1)

    async def test_resume_node_not_found(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="missing")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})
        mocks["content"].get_node = AsyncMock(return_value=None)
        with pytest.raises(ScenarioNotFoundError):
            await service.resume(char_id)

    async def test_finalize_master_not_found(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="missing", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_master = AsyncMock(return_value=None)
        with pytest.raises(ScenarioNotFoundError):
            await service.finalize(char_id)

    async def test_step_invalid_action(self, service, mocks):
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
        with pytest.raises(InvalidActionError):
            await service.step(1, "a1")

    async def test_finalize_success(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="terminal")
        mocks["sessions"].get = AsyncMock(return_value=context)
        mocks["content"].get_master = AsyncMock(return_value={"id": "q1"})

        mock_handler = MagicMock()
        result = MagicMock()
        result.rewards.items = ["item1"]
        result.rewards.skills = ["skill1"]
        result.rewards.attribute_bonuses = {"str": 1}
        mock_handler.on_finalize = AsyncMock(return_value=result)

        with patch("src.backend.features.scenario.services.scenario_service.get_handler", return_value=mock_handler):
            mocks["character_sessions"].apply_attribute_bonus = AsyncMock()
            mocks["character_sessions"].transition_state = AsyncMock()
            mocks["character_sessions"].clear_scenario_session = AsyncMock()
            mocks["sessions"].delete = AsyncMock()
            mocks["repo"].delete_state = AsyncMock()
            mocks["events"].publish = AsyncMock()

            await service.finalize(char_id)

            mocks["character_sessions"].transition_state.assert_called_with(
                char_id, CoreDomain.EXPLORATION, expected_state=CoreDomain.SCENARIO
            )
            mocks["sessions"].delete.assert_called_with(char_id)
