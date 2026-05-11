from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.dto.finalize import ScenarioFinalizeResult
from src.backend.features.scenario.exceptions import (
    InvalidScenarioAction,
    ScenarioNodeNotFound,
    ScenarioSessionNotFound,
)
from src.backend.features.scenario.services.scenario_service import ScenarioService
from src.shared.enums import CoreDomain


@pytest.mark.unit
class TestScenarioService:
    @pytest.fixture
    def mocks(self):
        return {
            "integrator": MagicMock(),
            "evaluator": MagicMock(),
            "director": MagicMock(),
            "formatter": MagicMock(),
        }

    @pytest.fixture
    def service(self, mocks):
        return ScenarioService(**mocks)

    async def test_initialize_success(self, service, mocks):
        import uuid
        char_id = 1
        quest_key = "q1"
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})

        mock_handler = MagicMock()
        context = ScenarioContextDTO(
            quest_key=quest_key,
            current_node_key="n1",
            scenario_session_id=uuid.uuid4()
        )
        mock_handler.on_initialize = AsyncMock(return_value=context)

        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].prepare_session = AsyncMock()
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
        mocks["integrator"].publish_event = AsyncMock()
        mocks["formatter"].render_payload.return_value = MagicMock(node_key="n1", buttons=[])

        result = await service.initialize(char_id, quest_key)
        assert result.node_key == "n1"
        mocks["integrator"].prepare_session.assert_called_once()

    async def test_initialize_not_found(self, service, mocks):
        mocks["integrator"].get_quest_master = AsyncMock(return_value=None)
        with pytest.raises(ScenarioNodeNotFound):
            await service.initialize(1, "unknown")

    async def test_resume_success(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
        mocks["formatter"].render_payload.return_value = MagicMock(node_key="n1", buttons=[])
        mocks["integrator"].publish_event = AsyncMock()

        result = await service.resume(char_id)
        assert result.node_key == "n1"


    async def test_resume_not_found(self, service, mocks):
        mocks["integrator"].load_session = AsyncMock(return_value=None)
        mocks["integrator"].publish_event = AsyncMock()
        with pytest.raises(ScenarioSessionNotFound):
            await service.resume(1)

    async def test_step_success(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"a1": {"type": "move"}}})

        mock_resolved = MagicMock()
        mock_resolved.node = {"node_key": "n2"}
        mock_resolved.context = {}
        mocks["director"].resolve_next_node = AsyncMock(return_value=mock_resolved)

        mocks["integrator"].update_progress = AsyncMock()
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})
        mocks["integrator"].publish_event = AsyncMock()

        await service.step(char_id, "a1")
        assert context.current_node_key == "n2"
        mocks["integrator"].update_progress.assert_called_once()

    async def test_step_terminal(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"a1": {"type": "move"}}})

        mock_resolved = MagicMock()
        mock_resolved.node = {"node_key": "end", "is_terminal": True}
        mock_resolved.context = {}
        mocks["director"].resolve_next_node = AsyncMock(return_value=mock_resolved)

        mocks["integrator"].update_progress = AsyncMock()
        mocks["integrator"].publish_event = AsyncMock()

        # Mock finalize
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})
        mock_handler = MagicMock()
        mock_result = MagicMock()
        mock_result.rewards.items = []
        mock_result.rewards.skills = []
        mock_result.rewards.attribute_bonuses = None
        mock_handler.on_finalize = AsyncMock(return_value=mock_result)
        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].finalize_session = AsyncMock()
        mocks["integrator"].grant_inventory_rewards = AsyncMock()
        mocks["integrator"].unlock_skills = AsyncMock()
        mocks["integrator"].apply_attribute_bonuses = AsyncMock()
        mocks["integrator"].request_combat_start = AsyncMock()
        mocks["integrator"].sync_active_character_to_db = AsyncMock()

        await service.step(char_id, "a1")
        mocks["integrator"].finalize_session.assert_called_with(char_id, CoreDomain.EXPLORATION)
        mocks["integrator"].sync_active_character_to_db.assert_called_with(char_id)

    async def test_finalize_shadow_combat_closes_scenario_to_exploration_before_combat(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="terminal")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"quest_key": "awakening_rift"})

        mock_handler = MagicMock()
        mock_handler.on_finalize = AsyncMock(
            return_value=ScenarioFinalizeResult(
                target_state=CoreDomain.COMBAT,
                transition_reason="scenario_shadow_combat",
                location_id="52_58",
                metadata={"battle_type": "shadow"},
            )
        )

        calls = []

        async def finalize_session(*args, **kwargs):
            calls.append(("finalize_session", args, kwargs))

        async def sync_active_character_to_db(*args):
            calls.append(("sync_active_character_to_db", args))

        async def request_combat_start(*args, **kwargs):
            calls.append(("request_combat_start", args, kwargs))
            return {"status": "ready", "combat_id": "combat-1"}

        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].grant_inventory_rewards = AsyncMock(return_value=[])
        mocks["integrator"].unlock_skills = AsyncMock()
        mocks["integrator"].apply_attribute_bonuses = AsyncMock()
        mocks["integrator"].prepare_combat_return_context = AsyncMock()
        mocks["integrator"].request_combat_start = AsyncMock(side_effect=request_combat_start)
        mocks["integrator"].finalize_session = AsyncMock(side_effect=finalize_session)
        mocks["integrator"].enter_prepared_combat = AsyncMock()
        mocks["integrator"].publish_event = AsyncMock()
        mocks["integrator"].sync_active_character_to_db = AsyncMock(side_effect=sync_active_character_to_db)

        result = await service.finalize(char_id)

        mocks["integrator"].prepare_combat_return_context.assert_awaited_once_with(char_id, location_id="52_58")
        assert calls[0] == (
            "finalize_session",
            (char_id, CoreDomain.EXPLORATION),
            {"prev_state": CoreDomain.EXPLORATION},
        )
        assert calls[1] == ("sync_active_character_to_db", (char_id,))
        assert calls[2] == (
            "request_combat_start",
            (char_id, "awakening_rift"),
            {"battle_type": "shadow", "location_id": "52_58"},
        )
        mocks["integrator"].enter_prepared_combat.assert_awaited_once_with(char_id, "combat-1")
        assert mocks["integrator"].sync_active_character_to_db.await_count == 2
        assert result.target_state == CoreDomain.COMBAT
        assert result.combat_id == "combat-1"

    async def test_initialize_auto_chain(self, service, mocks):
        import uuid
        char_id = 1
        quest_key = "q1"
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})

        mock_handler = MagicMock()
        context = ScenarioContextDTO(
            quest_key=quest_key,
            current_node_key="n1",
            scenario_session_id=uuid.uuid4()
        )
        mock_handler.on_initialize = AsyncMock(return_value=context)

        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].prepare_session = AsyncMock()
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"auto": {}}})

        mocks["director"]._get_node_actions = MagicMock(return_value={"auto": {}})
        mock_resolved = MagicMock()
        mock_resolved.node = {"node_key": "n2"}
        mock_resolved.context = {"foo": "bar"}
        mocks["director"].execute_auto_chain = AsyncMock(return_value=mock_resolved)

        mocks["integrator"].update_progress = AsyncMock()
        mocks["formatter"].render_payload.return_value = MagicMock(node_key="n2", buttons=[])
        mocks["integrator"].publish_event = AsyncMock()

        await service.initialize(char_id, quest_key)

        assert context.current_node_key == "n2"
        mocks["director"].execute_auto_chain.assert_called_once()



    async def test_initialize_state_transition_error(self, service, mocks):
        import uuid

        from src.backend.features.character.managers.session import StateTransitionError
        char_id = 1
        quest_key = "q1"
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})

        mock_handler = MagicMock()
        context = ScenarioContextDTO(quest_key=quest_key, current_node_key="n1", scenario_session_id=uuid.uuid4())
        mock_handler.on_initialize = AsyncMock(return_value=context)

        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].prepare_session = AsyncMock(side_effect=StateTransitionError("fail"))
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
        mocks["formatter"].render_payload.return_value = MagicMock(node_key="n1", buttons=[])
        mocks["integrator"].publish_event = AsyncMock()

        # Should bubble up
        with pytest.raises(StateTransitionError):
            await service.initialize(char_id, quest_key)

    async def test_step_invalid_condition(self, service, mocks):
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"a1": {"condition": "fail"}}})
        mocks["evaluator"].check_condition.return_value = False
        from src.backend.features.scenario.exceptions import ScenarioConditionFailed
        with pytest.raises(ScenarioConditionFailed):
            await service.step(1, "a1")

    async def test_step_finish_quest(self, service, mocks):
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"a1": {"type": "finish_quest"}}})

        # Mock finalize
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})
        mock_handler = MagicMock()
        mock_result = MagicMock()
        mock_result.rewards.items = []
        mock_result.rewards.skills = []
        mock_result.rewards.attribute_bonuses = None
        mock_handler.on_finalize = AsyncMock(return_value=mock_result)

        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].finalize_session = AsyncMock()
        mocks["integrator"].grant_inventory_rewards = AsyncMock()
        mocks["integrator"].unlock_skills = AsyncMock()
        mocks["integrator"].apply_attribute_bonuses = AsyncMock()
        mocks["integrator"].request_combat_start = AsyncMock()
        mocks["integrator"].enter_prepared_combat = AsyncMock()
        mocks["integrator"].publish_event = AsyncMock()
        mocks["integrator"].sync_active_character_to_db = AsyncMock()

        # Mock director._get_node_actions so ScenarioService knows it's a finish_quest action
        mocks["director"]._get_node_actions.return_value = {"a1": {"type": "finish_quest"}}

        await service.step(1, "a1")
        mocks["integrator"].finalize_session.assert_called_once()
        mocks["integrator"].sync_active_character_to_db.assert_called_once_with(1)

    async def test_resume_auto_chain(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {"auto": {}}})

        mocks["director"]._get_node_actions = MagicMock(return_value={"auto": {}})
        mock_resolved = MagicMock()
        mock_resolved.node = {"node_key": "n2"}
        mock_resolved.context = {"foo": "bar"}
        mocks["director"].execute_auto_chain = AsyncMock(return_value=mock_resolved)

        mocks["integrator"].update_progress = AsyncMock()
        mocks["formatter"].render_payload.return_value = MagicMock(node_key="n2", buttons=[])
        mocks["integrator"].publish_event = AsyncMock()

        await service.resume(char_id)
        assert context.current_node_key == "n2"
        mocks["director"].execute_auto_chain.assert_called_once()

    async def test_resume_master_not_found(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="missing", current_node_key="n1")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value=None)
        with pytest.raises(ScenarioNodeNotFound):
            await service.resume(char_id)

    async def test_step_session_not_found(self, service, mocks):
        mocks["integrator"].load_session = AsyncMock(return_value=None)
        with pytest.raises(ScenarioSessionNotFound):
            await service.step(1, "a1")

    async def test_step_finish_missing_session_recovers_to_exploration(self, service, mocks):
        mocks["integrator"].load_session = AsyncMock(return_value=None)
        mocks["integrator"].recover_missing_finish_to_exploration = AsyncMock()
        mocks["integrator"].sync_active_character_to_db = AsyncMock()
        mocks["integrator"].publish_event = AsyncMock()

        result = await service.step(1, "finish")

        assert result.target_state == CoreDomain.EXPLORATION
        assert result.transition_reason == "scenario_session_missing_recovered"
        assert result.metadata == {"recovered": True, "missing_session": True}
        mocks["integrator"].recover_missing_finish_to_exploration.assert_awaited_once_with(1)
        mocks["integrator"].sync_active_character_to_db.assert_awaited_once_with(1)
        mocks["integrator"].publish_event.assert_awaited_once()

    async def test_finalize_session_not_found(self, service, mocks):
        mocks["integrator"].load_session = AsyncMock(return_value=None)
        with pytest.raises(ScenarioSessionNotFound):
            await service.finalize(1)

    async def test_resume_node_not_found(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="missing")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})
        mocks["integrator"].get_node = AsyncMock(return_value=None)
        with pytest.raises(ScenarioNodeNotFound):
            await service.resume(char_id)

    async def test_finalize_master_not_found(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="missing", current_node_key="n1")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value=None)
        with pytest.raises(ScenarioNodeNotFound):
            await service.finalize(char_id)

    async def test_step_invalid_action(self, service, mocks):
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
        mocks["director"]._get_node_actions = MagicMock(return_value={})
        with pytest.raises(InvalidScenarioAction):
            await service.step(1, "a1")

    async def test_finalize_success(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="terminal")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})

        mock_handler = MagicMock()
        result = MagicMock()
        result.rewards.items = ["item1"]
        result.rewards.skills = ["skill1"]
        result.rewards.attribute_bonuses = {"str": 1}
        mock_handler.on_finalize = AsyncMock(return_value=result)

        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].grant_inventory_rewards = AsyncMock()
        mocks["integrator"].unlock_skills = AsyncMock()
        mocks["integrator"].apply_attribute_bonuses = AsyncMock()
        mocks["integrator"].request_combat_start = AsyncMock()
        mocks["integrator"].enter_prepared_combat = AsyncMock()
        mocks["integrator"].finalize_session = AsyncMock()
        mocks["integrator"].publish_event = AsyncMock()
        mocks["integrator"].sync_active_character_to_db = AsyncMock()

        await service.finalize(char_id)

        mocks["integrator"].finalize_session.assert_called_with(char_id, CoreDomain.EXPLORATION)
        mocks["integrator"].sync_active_character_to_db.assert_called_with(char_id)
