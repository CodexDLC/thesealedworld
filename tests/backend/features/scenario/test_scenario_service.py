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
from src.shared.schemas import ScenarioReturnContextDTO


@pytest.mark.unit
class TestScenarioService:
    @pytest.fixture
    def mocks(self):
        integrator = MagicMock()
        integrator.apply_finalize_effects = AsyncMock(return_value={})
        integrator.attach_npc_context = AsyncMock()
        integrator.apply_action_effects = AsyncMock(return_value={})
        integrator.prepare_exploration_return_context = AsyncMock()
        return {
            "integrator": integrator,
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
        mock_handler.on_initialize.assert_awaited_once_with(char_id, {"id": "q1"}, return_context=None, npc_key=None)

    async def test_initialize_passes_return_context_to_handler(self, service, mocks):
        import uuid

        char_id = 1
        quest_key = "q1"
        return_context = ScenarioReturnContextDTO(
            source_state=CoreDomain.CITY_SERVICES,
            return_state=CoreDomain.CITY_SERVICES,
            return_screen="bar",
            source_service_id="svc_tavern_hub",
            location_id="53_53",
            tavern_id="last_refuge",
        )
        master = {"quest_key": quest_key, "scenario_type": "dialogue_scenario", "start_node_id": "n1"}
        mocks["integrator"].get_quest_master = AsyncMock(return_value=master)

        mock_handler = MagicMock()
        context = ScenarioContextDTO(
            quest_key=quest_key,
            current_node_key="n1",
            scenario_session_id=uuid.uuid4(),
        )
        mock_handler.on_initialize = AsyncMock(return_value=context)

        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].prepare_session = AsyncMock()
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
        mocks["integrator"].publish_event = AsyncMock()
        mocks["formatter"].render_payload.return_value = MagicMock(node_key="n1", buttons=[])

        result = await service.initialize(char_id, quest_key, return_context=return_context)

        assert result.node_key == "n1"
        assert context.return_context == return_context
        mock_handler.on_initialize.assert_awaited_once_with(
            char_id,
            master,
            return_context=return_context,
            npc_key=None,
        )

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

    async def test_step_prepares_rift_when_entering_prepare_node(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="overseer_dialogue_01")
        target_node = {
            "node_key": "crash_sequence_02",
            "metadata": {
                "rift_entry": {
                    "prepare_on_show": True,
                    "rift_key": "starter_rift",
                    "entry_reason": "knockout",
                }
            },
        }
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_node = AsyncMock(
            return_value={"node_key": "overseer_dialogue_01", "actions_logic": {"fall": {"to_node": "crash_sequence_02"}}}
        )
        mocks["integrator"].has_prepared_rift_entry = AsyncMock(return_value=False)
        mocks["integrator"].publish_rift_entry_requested = AsyncMock(return_value={"request_id": "rift-request-1"})

        mock_resolved = MagicMock()
        mock_resolved.node = target_node
        mock_resolved.context = {}
        mocks["director"].resolve_next_node = AsyncMock(return_value=mock_resolved)
        mocks["integrator"].update_progress = AsyncMock()
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"quest_key": "awakening_rift"})
        mocks["integrator"].publish_event = AsyncMock()
        mocks["formatter"].render_payload.return_value = MagicMock(node_key="crash_sequence_02", buttons=[])

        await service.step(char_id, "fall")

        mocks["integrator"].publish_rift_entry_requested.assert_awaited_once_with(
            char_id,
            context,
            target_node,
        )
        assert context.flags["rift_entry_status"] == "requested"
        assert context.flags["rift_entry_request_id"] == "rift-request-1"
        assert mocks["integrator"].update_progress.await_count == 2

    async def test_enter_prepared_rift_action_activates_existing_run_without_requesting_new_one(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="crash_sequence_02")
        current_node = {
            "node_key": "crash_sequence_02",
            "actions_logic": {"fall": {"type": "enter_prepared_rift"}},
        }
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_node = AsyncMock(return_value=current_node)
        mocks["director"]._get_node_actions.return_value = current_node["actions_logic"]
        mocks["integrator"].has_prepared_rift_entry = AsyncMock(return_value=True)
        mocks["integrator"].activate_prepared_rift_entry = AsyncMock(
            return_value={
                "rift_session_id": "rift-run-1",
                "rift_instance_id": "rift-instance-1",
            }
        )
        mocks["integrator"].sync_active_character_to_db = AsyncMock()
        mocks["integrator"].publish_event = AsyncMock()

        result = await service.step(char_id, "fall")

        assert result.target_state == CoreDomain.RIFT
        assert result.transition_reason == "scenario_rift_entry"
        assert result.metadata["rift_session_id"] == "rift-run-1"
        mocks["integrator"].activate_prepared_rift_entry.assert_awaited_once_with(char_id, context)
        mocks["integrator"].publish_rift_entry_requested.assert_not_called()
        mocks["integrator"].sync_active_character_to_db.assert_awaited_once_with(char_id)

    async def test_initialize_attaches_npc_context_when_npc_key_resolved(self, service, mocks):
        import uuid

        char_id = 1
        quest_key = "q1"
        master = {"quest_key": quest_key, "start_node_id": "n1", "npc_key": "portal_pad_guide"}
        mocks["integrator"].get_quest_master = AsyncMock(return_value=master)

        mock_handler = MagicMock()
        context = ScenarioContextDTO(
            quest_key=quest_key,
            current_node_key="n1",
            scenario_session_id=uuid.uuid4(),
            npc_key="portal_pad_guide",
        )
        mock_handler.on_initialize = AsyncMock(return_value=context)

        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].prepare_session = AsyncMock()
        mocks["integrator"].get_node = AsyncMock(return_value={"node_key": "n1", "actions_logic": {}})
        mocks["integrator"].publish_event = AsyncMock()
        mocks["formatter"].render_payload.return_value = MagicMock(node_key="n1", buttons=[])

        await service.initialize(char_id, quest_key)

        mocks["integrator"].attach_npc_context.assert_awaited_once_with(char_id, context)

    async def test_step_applies_action_effects_and_refreshes_npc_context(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="n1", npc_key="portal_pad_guide")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_node = AsyncMock(
            return_value={"node_key": "n1", "actions_logic": {"a1": {"type": "move", "effects": [{"type": "npc.set_flag"}]}}}
        )

        mock_resolved = MagicMock()
        mock_resolved.node = {"node_key": "n2"}
        mock_resolved.context = {}
        mocks["director"].resolve_next_node = AsyncMock(return_value=mock_resolved)
        mocks["integrator"].update_progress = AsyncMock()
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"quest_key": "q1"})
        mocks["integrator"].publish_event = AsyncMock()

        await service.step(char_id, "a1")

        mocks["integrator"].apply_action_effects.assert_awaited_once()
        mocks["integrator"].attach_npc_context.assert_awaited_once_with(char_id, context)

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
        mock_result.location_id = None
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

    async def test_finalize_pve_combat_closes_scenario_only_after_combat_ready(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="terminal")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"quest_key": "awakening_rift"})

        mock_handler = MagicMock()
        mock_handler.on_finalize = AsyncMock(
            return_value=ScenarioFinalizeResult(
                target_state=CoreDomain.COMBAT,
                transition_reason="scenario_pve_combat",
                location_id="45_52",
                metadata={"battle_type": "pve"},
            )
        )

        calls = []

        async def finalize_session(*args, **kwargs):
            calls.append(("finalize_session", args, kwargs))

        async def sync_active_character_to_db(*args):
            calls.append(("sync_active_character_to_db", args, {}))

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

        mocks["integrator"].prepare_combat_return_context.assert_awaited_once_with(char_id, location_id="45_52")
        assert calls[0] == (
            "sync_active_character_to_db",
            (char_id,),
            {},
        )
        assert calls[1] == (
            "request_combat_start",
            (char_id, "awakening_rift"),
            {"battle_type": "pve", "location_id": "45_52"},
        )
        assert calls[2] == (
            "finalize_session",
            (char_id, CoreDomain.EXPLORATION),
            {"prev_state": CoreDomain.EXPLORATION},
        )
        mocks["integrator"].enter_prepared_combat.assert_awaited_once_with(char_id, "combat-1")
        assert mocks["integrator"].sync_active_character_to_db.await_count == 2
        assert result.target_state == CoreDomain.COMBAT
        assert result.combat_id == "combat-1"

    async def test_finalize_pve_combat_failure_keeps_scenario_session_open(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="terminal")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"quest_key": "awakening_rift"})

        mock_handler = MagicMock()
        mock_handler.on_finalize = AsyncMock(
            return_value=ScenarioFinalizeResult(
                target_state=CoreDomain.COMBAT,
                transition_reason="scenario_pve_combat",
                location_id="45_52",
                metadata={"battle_type": "pve"},
            )
        )
        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].grant_inventory_rewards = AsyncMock(return_value=[])
        mocks["integrator"].unlock_skills = AsyncMock()
        mocks["integrator"].apply_attribute_bonuses = AsyncMock()
        mocks["integrator"].prepare_combat_return_context = AsyncMock()
        mocks["integrator"].sync_active_character_to_db = AsyncMock()
        mocks["integrator"].request_combat_start = AsyncMock(side_effect=RuntimeError("monster group failed"))
        mocks["integrator"].finalize_session = AsyncMock()
        mocks["integrator"].enter_prepared_combat = AsyncMock()

        with pytest.raises(RuntimeError, match="monster group failed"):
            await service.finalize(char_id)

        mocks["integrator"].prepare_combat_return_context.assert_not_awaited()
        mocks["integrator"].finalize_session.assert_not_awaited()
        mocks["integrator"].enter_prepared_combat.assert_not_awaited()

    async def test_finalize_exploration_handoff_prepares_selected_location(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="awakening_rift", current_node_key="terminal")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"quest_key": "awakening_rift"})

        mock_handler = MagicMock()
        mock_handler.on_finalize = AsyncMock(
            return_value=ScenarioFinalizeResult(
                target_state=CoreDomain.EXPLORATION,
                transition_reason="scenario_outskirts_handoff",
                location_id="45_52",
                metadata={"quest_key": "awakening_rift"},
            )
        )
        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].grant_inventory_rewards = AsyncMock(return_value=[])
        mocks["integrator"].unlock_skills = AsyncMock()
        mocks["integrator"].apply_attribute_bonuses = AsyncMock()
        mocks["integrator"].request_combat_start = AsyncMock()
        mocks["integrator"].enter_prepared_combat = AsyncMock()
        mocks["integrator"].finalize_session = AsyncMock()
        mocks["integrator"].publish_event = AsyncMock()
        mocks["integrator"].sync_active_character_to_db = AsyncMock()

        result = await service.finalize(char_id)

        mocks["integrator"].prepare_exploration_return_context.assert_awaited_once_with(
            char_id,
            location_id="45_52",
        )
        mocks["integrator"].finalize_session.assert_awaited_once_with(char_id, CoreDomain.EXPLORATION)
        mocks["integrator"].request_combat_start.assert_not_awaited()
        mocks["integrator"].enter_prepared_combat.assert_not_awaited()
        assert result.transition_reason == "scenario_outskirts_handoff"

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

        from src.backend.infrastructure.actor_state.managers import StateTransitionError
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
        mock_result.location_id = None
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
        result.location_id = None
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

    async def test_finalize_applies_structured_effect_metadata(self, service, mocks):
        char_id = 1
        context = ScenarioContextDTO(quest_key="q1", current_node_key="terminal")
        mocks["integrator"].load_session = AsyncMock(return_value=context)
        mocks["integrator"].get_quest_master = AsyncMock(return_value={"id": "q1"})

        mock_handler = MagicMock()
        result = ScenarioFinalizeResult(
            target_state=CoreDomain.CITY_SERVICES,
            transition_reason="dialogue_finalized",
            location_id="53_53",
            metadata={"next_screen": "room", "_effects": [{"type": "tavern.grant_room", "required": True}]},
        )
        mock_handler.on_finalize = AsyncMock(return_value=result)

        mocks["integrator"].build_handler.return_value = mock_handler
        mocks["integrator"].grant_inventory_rewards = AsyncMock(return_value=[])
        mocks["integrator"].unlock_skills = AsyncMock()
        mocks["integrator"].apply_attribute_bonuses = AsyncMock()
        mocks["integrator"].request_combat_start = AsyncMock()
        mocks["integrator"].enter_prepared_combat = AsyncMock()
        mocks["integrator"].finalize_session = AsyncMock()
        mocks["integrator"].publish_event = AsyncMock()
        mocks["integrator"].sync_active_character_to_db = AsyncMock()
        mocks["integrator"].apply_finalize_effects = AsyncMock(return_value={"room_granted": True, "room_id": 10})

        finalized = await service.finalize(char_id)

        mocks["integrator"].apply_finalize_effects.assert_awaited_once()
        effect_args = mocks["integrator"].apply_finalize_effects.await_args
        assert effect_args.args[0] == char_id
        assert effect_args.args[1]["next_screen"] == "room"
        assert effect_args.args[1]["_effects"] == [{"type": "tavern.grant_room", "required": True}]
        assert effect_args.kwargs == {"quest_key": "q1"}
        assert finalized.metadata["room_granted"] is True
        assert finalized.metadata["room_id"] == 10
        mocks["integrator"].prepare_exploration_return_context.assert_not_awaited()
        mocks["integrator"].finalize_session.assert_called_with(char_id, CoreDomain.CITY_SERVICES)
