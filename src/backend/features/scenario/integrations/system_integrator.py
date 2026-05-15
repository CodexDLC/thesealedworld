from __future__ import annotations

import json
import logging
import uuid
from time import perf_counter
from typing import TYPE_CHECKING, Any

from src.backend.config.settings import settings
from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.character.events import CharacterEvents
from src.backend.features.inventory.events.publisher import InventoryEvents
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, ItemOriginRefDTO, ItemPlacementRefDTO
from src.backend.features.items.events.publisher import ItemEvents
from src.backend.features.scenario.dto.context import ScenarioContextDTO
from src.backend.features.scenario.handlers import get_handler
from src.backend.features.scenario.handlers.base_handler import ScenarioInitialHandlerContext
from src.backend.features.tavern.events import TavernEvents
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from src.backend.core.bus import GameEventProducer
    from src.backend.features.character.managers import CharacterSessionManager
    from src.backend.features.character.repositories import CharacterRepository
    from src.backend.features.scenario.handlers import BaseScenarioHandler
    from src.backend.features.scenario.integrations.content_integration import ScenarioContentIntegration
    from src.backend.infrastructure.scenario.managers.session_manager import ScenarioSessionManager
    from src.backend.infrastructure.scenario.repositories import ScenarioRepository

log = logging.getLogger(__name__)
BACKUP_INTERVAL = 3
SCENARIO_COMBAT_TTL_SECONDS = 24 * 60 * 60


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)


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
        content: ScenarioContentIntegration,
        character_sessions: CharacterSessionManager,
        repo: ScenarioRepository,
        events: GameEventProducer,
        character_repo: CharacterRepository | None = None,
    ) -> None:
        self.sessions = sessions
        self.content = content
        self.character_sessions = character_sessions
        self.repo = repo
        self.events = events
        self.character_repo = character_repo

    # --- Session Management (Redis & DB) ---

    async def ensure_character_owner(self, *, user_id: uuid.UUID, char_id: int) -> None:
        if self.character_repo is None:
            raise RuntimeError("Scenario character repository is not configured")
        character = await self.character_repo.get_by_id_and_user_id(char_id, user_id)
        if character is None:
            raise BusinessLogicException("Scenario character is unavailable")

    def build_handler(self, quest_master: dict[str, Any]) -> BaseScenarioHandler:
        quest_key = str(quest_master["quest_key"])
        scenario_type = str(quest_master["scenario_type"])
        return get_handler(quest_key, scenario_type=scenario_type, integration=self)

    async def get_initial_handler_context(self, char_id: int) -> ScenarioInitialHandlerContext:
        symbiote = await self.character_sessions.get_section(char_id, "symbiote")
        sys_actor = settings.default_symbiote_name
        if isinstance(symbiote, dict):
            sys_actor = str(symbiote.get("name") or sys_actor)
        elif isinstance(symbiote, str) and symbiote:
            sys_actor = symbiote

        location = await self.character_sessions.get_section(char_id, "location")
        prev_loc = location.get("current") if isinstance(location, dict) else "52_52"

        state = await self.character_sessions.get_section(char_id, "state")
        return ScenarioInitialHandlerContext(
            sys_actor=sys_actor,
            prev_state=str(state) if state else None,
            prev_loc=prev_loc,
        )

    async def prepare_session(self, char_id: int, quest_key: str, context: ScenarioContextDTO) -> None:
        """Sets up the initial state for a scenario session across all stores."""
        # 1. Create Scenario Session
        await self.sessions.create(char_id, context)

        # 2. Register with Character Session
        try:
            expected_state = self._prepare_expected_state(context)
            await self.character_sessions.transition_state(
                char_id,
                CoreDomain.SCENARIO,
                expected_state=expected_state,
                prev_state=expected_state,
            )
        except Exception:
            await self.sessions.delete(char_id)
            raise

        await self.character_sessions.set_scenario_session(
            char_id,
            str(context.scenario_session_id),
            active_quest=quest_key,
        )

        # 3. Create initial DB Backup
        await self._backup_state(char_id, quest_key, context.current_node_key, context, context.scenario_session_id)

    @staticmethod
    def _prepare_expected_state(context: ScenarioContextDTO) -> CoreDomain | str | None:
        if context.return_context is not None:
            return context.return_context.source_state
        return context.prev_state

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

    async def finalize_session(
        self,
        char_id: int,
        target_state: CoreDomain = CoreDomain.EXPLORATION,
        *,
        prev_state: CoreDomain | None = None,
    ) -> None:
        """Cleans up all session artifacts across all stores."""
        await self.character_sessions.transition_state(
            char_id,
            target_state,
            expected_state=CoreDomain.SCENARIO,
            prev_state=prev_state,
        )
        await self.character_sessions.clear_scenario_session(char_id)
        await self.sessions.delete(char_id)
        await self.repo.delete_state(char_id)

    async def recover_missing_finish_to_exploration(self, char_id: int) -> None:
        """Recover stale scenario UI when the runtime scenario session is already gone."""
        current_state = await self.character_sessions.get_section(char_id, "state")
        if current_state is None:
            raise RuntimeError(f"Character session not found: char_id={char_id}")

        if current_state == CoreDomain.SCENARIO.value:
            await self.character_sessions.set_state(char_id, CoreDomain.EXPLORATION, prev_state=CoreDomain.SCENARIO)

        await self.character_sessions.clear_scenario_session(char_id)
        await self.sessions.delete(char_id)
        await self.repo.delete_state(char_id)

    async def enter_prepared_combat(self, char_id: int, combat_id: str) -> None:
        await self.character_sessions.set_combat_session(char_id, combat_id)
        await self.character_sessions.set_state(char_id, CoreDomain.COMBAT, prev_state=CoreDomain.EXPLORATION)

    async def cleanup_session(self, char_id: int) -> None:
        """Remove scenario artifacts without character state transitions."""
        await self.sessions.delete(char_id)
        await self.repo.delete_state(char_id)

    async def sync_active_character_to_db(self, char_id: int) -> None:
        started_at = perf_counter()
        response = await self.events.request(
            CharacterEvents.ACTIVE_SESSION_SYNC_REQUESTED,
            {"char_id": char_id},
            timeout=30.0,
        )
        log.info(
            "ScenarioIntegratorTiming | op=sync_active_character_to_db char_id=%s status=%s ms=%s",
            char_id,
            response.get("status") if isinstance(response, dict) else type(response).__name__,
            _elapsed_ms(started_at),
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
        return await self.content.get_master(quest_key)

    async def get_node(self, quest_key: str, node_key: str) -> dict[str, Any] | None:
        return await self.content.get_node(quest_key, node_key)

    async def get_nodes_by_pool(self, quest_key: str, pool_tag: str) -> list[dict[str, Any]]:
        return await self.content.get_nodes_by_pool(quest_key, pool_tag)

    # --- Rewards / Features Interaction ---

    async def grant_inventory_rewards(self, char_id: int, items: list[str], *, quest_key: str) -> list[str]:
        if not items:
            return []

        item_ids = await self.generate_reward_items(char_id, items, quest_key=quest_key)
        started_at = perf_counter()
        response = await self.events.request(
            InventoryEvents.REWARDS_GRANT_REQUESTED,
            {
                "char_id": char_id,
                "quest_key": quest_key,
                "item_ids": item_ids,
                "equip_if_possible": True,
            },
            timeout=30.0,
        )
        log.info(
            "ScenarioIntegratorTiming | op=inventory_rewards_grant char_id=%s quest_key=%s item_count=%s status=%s ms=%s",
            char_id,
            quest_key,
            len(item_ids),
            response.get("status") if isinstance(response, dict) else type(response).__name__,
            _elapsed_ms(started_at),
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Scenario inventory reward grant failed: {response!r}")
        granted_item_ids = [str(item_id) for item_id in response.get("item_ids", [])]
        log.info(
            "Scenario inventory rewards granted: char_id=%s quest_key=%s base_items=%s item_ids=%s",
            char_id,
            quest_key,
            items,
            granted_item_ids,
        )
        return granted_item_ids

    async def generate_reward_items(self, char_id: int, base_item_ids: list[str], *, quest_key: str) -> list[str]:
        base_item_ids = [base_id for base_id in base_item_ids if base_id]
        if not base_item_ids:
            return []

        requests = [
            ItemGenerationRequestDTO(
                base_id=base_id,
                rarity_tier=0,
                source=f"scenario:{quest_key}",
                char_id=char_id,
                request_ai_text=False,
                placement_ref=ItemPlacementRefDTO(
                    holder_type="character",
                    holder_id=str(char_id),
                    storage_type="backpack",
                    slot=None,
                ),
                origin_ref=ItemOriginRefDTO(origin_type="scenario", origin_ref=quest_key),
                delivery_mode="forward",
                return_item=False,
            ).model_dump(mode="json")
            for base_id in base_item_ids
        ]
        started_at = perf_counter()
        response = await self.events.request(
            ItemEvents.GENERATE_REQUESTED,
            {"items": requests, "delivery_mode": "forward", "return_items": False},
            timeout=30.0,
        )
        log.info(
            "ScenarioIntegratorTiming | op=generate_reward_items char_id=%s quest_key=%s base_count=%s status=%s ms=%s",
            char_id,
            quest_key,
            len(base_item_ids),
            response.get("status") if isinstance(response, dict) else type(response).__name__,
            _elapsed_ms(started_at),
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Scenario reward item generation failed: {response!r}")
        item_ids = [str(item_id) for item_id in response.get("item_ids", [])]
        if len(item_ids) != len(base_item_ids):
            raise RuntimeError(
                "Scenario reward item generation returned an unexpected item count: "
                f"expected={len(base_item_ids)} actual={len(item_ids)}"
            )
        log.info(
            "Scenario reward items generated: char_id=%s quest_key=%s base_items=%s item_ids=%s",
            char_id,
            quest_key,
            base_item_ids,
            item_ids,
        )
        return item_ids

    async def unlock_skills(self, char_id: int, skills: list[str], *, initial_xp: float | None = None) -> None:
        if not skills:
            return
        started_at = perf_counter()
        payload: dict[str, Any] = {"char_id": char_id, "skill_keys": json.dumps(skills), "progress_state": "PLUS"}
        if initial_xp is not None:
            payload["initial_xp"] = min(1.0, max(0.0, float(initial_xp)))
        response = await self.events.request(
            CharacterEvents.SKILLS_UNLOCK_REQUESTED,
            payload,
            timeout=30.0,
        )
        log.info(
            "ScenarioIntegratorTiming | op=unlock_skills char_id=%s skill_count=%s status=%s ms=%s",
            char_id,
            len(skills),
            response.get("status") if isinstance(response, dict) else type(response).__name__,
            _elapsed_ms(started_at),
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Scenario skill unlock failed: {response!r}")

    async def restore_character_vitals(self, char_id: int, *, reason: str) -> dict[str, Any]:
        started_at = perf_counter()
        response = await self.events.request(
            CharacterEvents.VITALS_RESTORE_REQUESTED,
            {"char_id": char_id, "reason": reason},
            timeout=30.0,
        )
        log.info(
            "ScenarioIntegratorTiming | op=restore_character_vitals char_id=%s status=%s ms=%s",
            char_id,
            response.get("status") if isinstance(response, dict) else type(response).__name__,
            _elapsed_ms(started_at),
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Scenario character vitals restore failed: {response!r}")
        vitals = response.get("vitals") or {}
        return vitals if isinstance(vitals, dict) else {}

    async def apply_attribute_bonuses(self, char_id: int, bonuses: dict[str, int]) -> None:
        if bonuses:
            await self.character_sessions.apply_attribute_bonus(char_id, bonuses)

    async def apply_finalize_effects(self, char_id: int, metadata: dict[str, Any], *, quest_key: str) -> dict[str, Any]:
        effects = metadata.pop("_effects", [])
        if not effects:
            return {}
        if not isinstance(effects, list):
            raise RuntimeError(f"Scenario finalize effects must be a list: quest_key={quest_key}")

        results: dict[str, Any] = {}
        for effect in effects:
            if not isinstance(effect, dict):
                raise RuntimeError(f"Scenario finalize effect must be an object: quest_key={quest_key}")
            effect_type = str(effect.get("type") or "")
            required = bool(effect.get("required", True))
            try:
                effect_result = await self._apply_finalize_effect(char_id, effect, quest_key=quest_key)
            except Exception:
                if required:
                    raise
                log.exception(
                    "Optional scenario finalize effect failed: char_id=%s quest_key=%s effect=%s",
                    char_id,
                    quest_key,
                    effect,
                )
                continue
            results.update(effect_result)
            results.setdefault("effects", {})[effect_type] = effect_result
        return results

    async def _apply_finalize_effect(self, char_id: int, effect: dict[str, Any], *, quest_key: str) -> dict[str, Any]:
        effect_type = str(effect.get("type") or "")
        if effect_type == "tavern.grant_room":
            response = await self.events.request(
                TavernEvents.ROOM_GRANT_REQUESTED,
                {
                    "char_id": char_id,
                    "quest_key": quest_key,
                    "tavern_id": str(effect["tavern_id"]),
                    "room_key": str(effect.get("room_key") or ""),
                    "reason": str(effect.get("reason") or f"scenario:{quest_key}"),
                },
                timeout=30.0,
            )
            if not isinstance(response, dict) or response.get("status") != "ok":
                raise RuntimeError(f"Tavern room grant effect failed: {response!r}")
            return {
                "room_granted": True,
                "room_id": response.get("room_id"),
                "room_key": response.get("room_key"),
                "tavern_id": response.get("tavern_id"),
                "room_created": response.get("created"),
            }
        raise RuntimeError(f"Unsupported scenario finalize effect: {effect_type}")

    async def prepare_combat_return_context(self, char_id: int, *, location_id: str | None = None) -> None:
        updates: dict[str, Any] = {"$.prev_state": CoreDomain.EXPLORATION.value}
        if location_id:
            updates["$.location.current"] = location_id
            updates["$.location.prev"] = location_id
        await self.character_sessions.patch_fields(char_id, updates)
        await self.character_sessions.mark_dirty(
            char_id, reason="combat_return_context_prepared", paths=sorted(updates)
        )

    async def request_combat_start(
        self,
        char_id: int,
        quest_key: str,
        *,
        battle_type: str = "shadow",
        location_id: str | None = None,
    ) -> dict[str, Any]:
        combat_id = str(uuid.uuid4())
        participants = {"team_1": [char_id]}
        started_at = perf_counter()
        await self.restore_character_vitals(char_id, reason=f"scenario:{quest_key}:combat_handoff")
        log.info(
            "ScenarioIntegratorTiming | op=restore_vitals_for_combat char_id=%s combat_id=%s ms=%s",
            char_id,
            combat_id,
            _elapsed_ms(started_at),
        )
        started_at = perf_counter()
        commitments = await self.prepare_combat_commitments(
            combat_id,
            player_ids=[char_id],
            monster_ids=[],
        )
        log.info(
            "ScenarioIntegratorTiming | op=prepare_combat_commitments_for_start char_id=%s combat_id=%s count=%s ms=%s",
            char_id,
            combat_id,
            len(commitments),
            _elapsed_ms(started_at),
        )
        started_at = perf_counter()
        response = await self.events.request(
            "combat.session_requested",
            {
                "source": f"scenario:{quest_key}",
                "combat_id": combat_id,
                "correlation_id": combat_id,
                "battle_type": battle_type,
                "requested_by": char_id,
                "participants": json.dumps(participants),
                "commitments": json.dumps(commitments),
                "location_id": location_id or "",
                "ttl": SCENARIO_COMBAT_TTL_SECONDS,
            },
            timeout=30.0,
            correlation_id=combat_id,
        )
        log.info(
            "ScenarioIntegratorTiming | op=combat_session_requested char_id=%s combat_id=%s status=%s ms=%s",
            char_id,
            combat_id,
            response.get("status") if isinstance(response, dict) else type(response).__name__,
            _elapsed_ms(started_at),
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

    async def prepare_combat_commitments(
        self,
        combat_id: str,
        *,
        player_ids: list[int],
        monster_ids: list[str],
    ) -> dict[str, str]:
        started_at = perf_counter()
        response = await self.events.request(
            CharacterEvents.COMBAT_COMMITMENTS_REQUESTED,
            {
                "scope_id": combat_id,
                "player_ids": json.dumps(player_ids),
                "monster_ids": json.dumps(monster_ids),
                "ttl": SCENARIO_COMBAT_TTL_SECONDS,
            },
            timeout=30.0,
        )
        log.info(
            "ScenarioIntegratorTiming | op=prepare_combat_commitments combat_id=%s player_count=%s monster_count=%s "
            "status=%s ms=%s",
            combat_id,
            len(player_ids),
            len(monster_ids),
            response.get("status") if isinstance(response, dict) else type(response).__name__,
            _elapsed_ms(started_at),
        )
        if not isinstance(response, dict) or response.get("status") not in ("ok", "partial"):
            raise RuntimeError(f"Scenario combat commitment preparation failed: {response!r}")
        commitments = response.get("commitments") or {}
        if isinstance(commitments, str):
            commitments = json.loads(commitments)
        if not isinstance(commitments, dict):
            raise RuntimeError(f"Scenario combat commitments response is invalid: {response!r}")
        return {str(key): str(value) for key, value in commitments.items() if value}

    async def publish_event(self, event_name: str, payload: dict[str, Any]) -> None:
        await self.events.publish(event_name, payload)
