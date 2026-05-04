from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING, Any

from src.backend.features.character.events import CharacterEvents
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, ItemOriginRefDTO, ItemPlacementRefDTO
from src.backend.features.items.events import ItemEvents
from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.dto.master import QuestMasterSchema, QuestNodeSchema
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from codex_platform.redis_service import RedisService

    from src.backend.core.bus import GameEventProducer
    from src.backend.infrastructure.actor_state import CharacterSessionManager
    from src.backend.infrastructure.scenario.managers.content_manager import ScenarioContentManager
    from src.backend.infrastructure.scenario.managers.session_manager import ScenarioSessionManager
    from src.backend.infrastructure.scenario.repositories import ScenarioRepository

log = logging.getLogger(__name__)
BACKUP_INTERVAL = 3


class ScenarioSystemIntegrator:
    """
    Central hub for coordinating feature logic with external infrastructure:
    - Redis scenario sessions
    - Redis global quest data
    - Redis Character sessions (ac:)
    - DB backups and state
    - Events
    """

    def __init__(
        self,
        sessions: ScenarioSessionManager,
        content_manager: ScenarioContentManager,
        character_sessions: CharacterSessionManager,
        repo: ScenarioRepository,
        events: GameEventProducer,
        redis: RedisService,
    ) -> None:
        self.sessions = sessions
        self.content_manager = content_manager
        self.character_sessions = character_sessions
        self.repo = repo
        self.events = events
        self.redis = redis

    # --- Session Management (Redis & DB) ---

    async def prepare_session(self, char_id: int, quest_key: str, context: ScenarioContextDTO) -> None:
        """Sets up the initial state for a scenario session across all stores."""
        # 1. Create Scenario Session
        await self.sessions.create(char_id, context)

        # 2. Register with Character Session
        try:
            await self.character_sessions.transition_state(
                char_id, CoreDomain.SCENARIO, expected_state=CoreDomain.LOBBY
            )
        except Exception:
            log.warning("Scenario initialize state transition skipped: char_id=%s", char_id)

        await self.character_sessions.set_scenario_session(
            char_id,
            str(context.scenario_session_id),
            active_quest=quest_key,
        )

        # 3. Create initial DB Backup
        await self._backup_state(char_id, quest_key, context.current_node_key, context, context.scenario_session_id)

    async def load_session(self, char_id: int) -> ScenarioContextDTO | None:
        """Loads a session, preferring Redis, falling back to DB."""
        context = await self.sessions.get(char_id)
        if context is not None:
            return context

        # Fallback to DB
        state = await self.repo.get_active_state(char_id)
        if not state:
            log.warning("Scenario backup repair unavailable: char_id=%s", char_id)
            return None

        context = ScenarioContextDTO.model_validate(state["context"])
        await self.sessions.create(char_id, context)
        await self.character_sessions.set_scenario_session(
            char_id,
            str(context.scenario_session_id),
            active_quest=context.quest_key,
        )
        log.info("Scenario session repaired from backup: char_id=%s quest_key=%s", char_id, context.quest_key)
        return context

    async def update_progress(self, char_id: int, context: ScenarioContextDTO, *, force_backup: bool = False) -> None:
        """Saves current progress to Redis and periodically to DB."""
        # Update Redis
        await self.sessions.patch(
            char_id,
            {
                "$.current_node_key": context.current_node_key,
                "$.step_counter": context.step_counter,
                "$.total_steps": context.total_steps,
                "$.visited_nodes": context.visited_nodes,
                "$.weights": context.weights.model_dump(mode="json"),
                "$.queues": context.queues.model_dump(mode="json"),
                "$.flags": context.flags,
                "$.updated_at": context.updated_at.isoformat(),
            },
        )

        # DB Backup
        if force_backup or context.step_counter % BACKUP_INTERVAL == 0:
            await self._backup_state(
                char_id, context.quest_key, context.current_node_key, context, context.scenario_session_id
            )

    async def finalize_session(self, char_id: int, target_state: CoreDomain = CoreDomain.EXPLORATION) -> None:
        """Cleans up all session artifacts across all stores."""
        await self.character_sessions.transition_state(char_id, target_state, expected_state=CoreDomain.SCENARIO)
        await self.character_sessions.clear_scenario_session(char_id)
        await self.sessions.delete(char_id)
        await self.repo.delete_state(char_id)

    async def sync_active_character_to_db(self, char_id: int) -> None:
        response = await self.events.request(
            CharacterEvents.ACTIVE_SESSION_SYNC_REQUESTED,
            {"char_id": char_id},
            timeout=30.0,
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Scenario active character sync failed: {response!r}")

    async def _backup_state(
        self, char_id: int, quest_key: str, node_key: str, context: ScenarioContextDTO, session_id: uuid.UUID
    ) -> None:
        await self.repo.upsert_state(
            char_id,
            quest_key,
            node_key,
            context.model_dump(mode="json"),
            session_id,
        )

    # --- Content Provider Methods ---

    async def get_quest_master(self, quest_key: str) -> dict[str, Any] | None:
        master = await self.content_manager.get_master(quest_key)
        if master:
            return QuestMasterSchema.model_validate(master).model_dump(mode="json")

        if await self._ensure_static_cache(quest_key):
            master = await self.content_manager.get_master(quest_key)
            if master:
                return QuestMasterSchema.model_validate(master).model_dump(mode="json")
        return None

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        node = await self.content_manager.get_node(quest_key, node_key)
        if node:
            return QuestNodeSchema.model_validate(node).model_dump(mode="json")

        if await self._ensure_static_cache(quest_key):
            node = await self.content_manager.get_node(quest_key, node_key)
            if node:
                return QuestNodeSchema.model_validate(node).model_dump(mode="json")
        return None

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        await self._ensure_static_cache(quest_key)
        # For pools, it's safer to fetch from DB and validate, or filter Redis nodes
        nodes = await self.repo.get_nodes_by_pool(quest_key, pool_tag)
        return [QuestNodeSchema.model_validate(node).model_dump(mode="json") for node in nodes]

    async def _ensure_static_cache(self, quest_key: str) -> bool:
        if await self.content_manager.exists(quest_key):
            return True

        log.info("ScenarioIntegrator | Cache MISS for '%s'. Loading from DB...", quest_key)
        master = await self.repo.get_master(quest_key)
        if not master:
            return False

        nodes = await self.repo.get_all_quest_nodes(quest_key)
        await self.content_manager.cache_quest_data(quest_key, master, nodes)
        return True

    # --- Rewards / Features Interaction ---

    async def grant_inventory_rewards(self, char_id: int, items: list[str], *, quest_key: str) -> list[str]:
        if not items:
            return []

        requests = [
            ItemGenerationRequestDTO(
                base_id=base_id,
                rarity_tier=0,
                source=f"scenario:{quest_key}",
                char_id=char_id,
                request_ai_text=True,
                placement_ref=ItemPlacementRefDTO(
                    holder_type="character",
                    holder_id=str(char_id),
                    storage_type="backpack",
                ),
                origin_ref=ItemOriginRefDTO(origin_type="scenario", origin_ref=quest_key),
                delivery_mode="forward",
                return_item=False,
            ).model_dump(mode="json")
            for base_id in items
        ]
        response = await self.events.request(
            ItemEvents.GENERATE_REQUESTED,
            {"items": requests, "delivery_mode": "forward", "return_items": False},
            timeout=30.0,
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Scenario item reward generation failed: {response!r}")
        item_ids = [str(item_id) for item_id in response.get("item_ids", [])]
        log.info(
            "Scenario inventory rewards generated: char_id=%s quest_key=%s base_items=%s item_ids=%s",
            char_id,
            quest_key,
            items,
            item_ids,
        )
        return item_ids

    async def unlock_skills(self, char_id: int, skills: list[str]) -> None:
        if not skills:
            return
        response = await self.events.request(
            CharacterEvents.SKILLS_UNLOCK_REQUESTED,
            {"char_id": char_id, "skill_keys": json.dumps(skills), "progress_state": "PLUS"},
            timeout=30.0,
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Scenario skill unlock failed: {response!r}")

    async def apply_attribute_bonuses(self, char_id: int, bonuses: dict[str, int]) -> None:
        if bonuses:
            await self.character_sessions.apply_attribute_bonus(char_id, bonuses)

    async def prepare_combat_return_context(self, char_id: int, *, location_id: str | None = None) -> None:
        updates: dict[str, Any] = {"$.prev_state": CoreDomain.EXPLORATION.value}
        if location_id:
            updates["$.location.current"] = location_id
            updates["$.location.previous"] = location_id
        await self.character_sessions.patch_fields(char_id, updates)

    async def request_combat_start(
        self,
        char_id: int,
        quest_key: str,
        *,
        battle_type: str = "shadow",
        location_id: str | None = None,
    ) -> dict[str, Any]:
        combat_id = str(uuid.uuid4())
        response = await self.events.request(
            "combat.session_requested",
            {
                "source": f"scenario:{quest_key}",
                "combat_id": combat_id,
                "correlation_id": combat_id,
                "battle_type": battle_type,
                "requested_by": char_id,
                "participants": json.dumps({"team_1": [char_id]}),
                "location_id": location_id or "",
            },
            timeout=30.0,
            correlation_id=combat_id,
        )
        if not isinstance(response, dict) or response.get("status") != "ready":
            raise RuntimeError(f"Scenario combat start failed: {response!r}")
        log.info(
            "Scenario shadow combat requested: char_id=%s quest_key=%s combat_id=%s location_id=%s",
            char_id,
            quest_key,
            response.get("combat_id"),
            location_id,
        )
        return response

    async def publish_event(self, event_name: str, payload: dict[str, Any]) -> None:
        await self.events.publish(event_name, payload)
