from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
from src.backend.features.scenario.exceptions import ScenarioSessionNotFound
from src.shared.enums import CoreDomain

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.features.character.integrations import CharacterStateIntegrator
    from src.backend.features.rift.integrations import RiftRuntimeIntegration
    from src.backend.features.scenario.services import ScenarioService
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager
    from src.backend.infrastructure.loot.managers.loot_manager import LootManager
    from src.shared.schemas import ScenarioPayloadDTO


@dataclass(frozen=True, slots=True)
class GameSessionCharacter:
    character_id: int
    name: str
    game_stage: str | None
    prev_game_stage: str | None


class GameSessionIntegrator:
    """Facade over active character runtime state for game session entry."""

    def __init__(
        self,
        *,
        character_repo: CharacterRepository | None = None,
        character_sessions: CharacterSessionManager | None = None,
        db_session: AsyncSession | None = None,
        scenario_service: ScenarioService | None = None,
        expedition_service: Any | None = None,
        state_integrator: CharacterStateIntegrator | None = None,
        loot_manager: LootManager | None = None,
        loot_arq: Any | None = None,
        rift_runtime: RiftRuntimeIntegration | None = None,
        starter_reset_integration: Any | None = None,
    ) -> None:
        if character_repo is None and db_session is not None:
            character_repo = CharacterRepository(db_session)
        self.character_repo = character_repo
        self.character_sessions = character_sessions
        self.scenario_service = scenario_service
        self.expedition_service = expedition_service
        self.state_integrator = state_integrator
        self.loot_manager = loot_manager
        self.loot_arq = loot_arq
        self.rift_runtime = rift_runtime
        self.starter_reset_integration = starter_reset_integration

    async def get_owned_character(self, character_id: int, user_id: UUID) -> GameSessionCharacter | None:
        if self.character_repo is None:
            return None
        character = await self.character_repo.get_by_id_and_user_id(character_id, user_id)
        if character is None:
            return None
        return GameSessionCharacter(
            character_id=character.character_id,
            name=character.name,
            game_stage=character.game_stage,
            prev_game_stage=character.prev_game_stage,
        )

    async def release_other_active_sessions(self, user_id: UUID, selected_character_id: int) -> None:
        if self.character_sessions is None:
            return
        if self.character_repo is None or self.scenario_service is None:
            raise RuntimeError("character_repo and scenario_service are required to release active sessions")

        characters = await self.character_repo.get_by_user_id(user_id)
        other_character_ids = [
            character.character_id for character in characters if character.character_id != selected_character_id
        ]
        if not other_character_ids:
            return

        sessions = await self.character_sessions.get_sessions_batch(other_character_ids)
        persisted_any = False
        for character_id, document in sessions.items():
            if not isinstance(document, dict):
                continue

            await self._persist_active_session_snapshot(character_id, document)
            persisted_any = True
            await self.scenario_service.cleanup(character_id)
            await self.character_sessions.delete_session(character_id)
            logger.bind(
                user_id=str(user_id),
                selected_char_id=selected_character_id,
                released_char_id=character_id,
            ).info("GameSessionPreviousActiveCharacterSessionReleased")

        if persisted_any:
            await self.character_repo.commit()

    async def get_active_session(self, character_id: int, user_id: UUID) -> CharacterSessionDocumentDTO | None:
        if self.character_sessions is None:
            return None

        document = await self.character_sessions.get_session(character_id)
        if document is None:
            if self.state_integrator is None:
                return None
            try:
                return await self.state_integrator.bootstrap_active_session(user_id, character_id)
            except Exception:
                logger.bind(char_id=character_id).exception("GameSessionColdActiveCharacterBootstrapFailed")
                return None

        try:
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
        except Exception:
            logger.bind(char_id=character_id).exception("GameSessionHotActiveCharacterValidationFailed")
            return None

        if session_doc.user_id != user_id:
            logger.bind(char_id=character_id, owner_id=str(session_doc.user_id), requested_by=str(user_id)).warning(
                "GameSessionHotActiveCharacterOwnershipMismatch"
            )
            return None

        return session_doc

    async def set_active_session_state(self, character_id: int, state: CoreDomain) -> None:
        if self.character_sessions is None:
            return
        await self.character_sessions.patch_fields(character_id, {"$.state": state.value})
        await self.character_sessions.mark_dirty(
            character_id,
            reason="game_session_state_fallback",
            paths=["$.state"],
        )

    async def reset_active_session_to_exploration(self, character_id: int) -> None:
        if self.character_sessions is None:
            return
        await self.character_sessions.reset_main_runtime_refs_to_exploration(character_id)

    async def respawn_character(self, character_id: int) -> dict[str, Any]:
        if self.expedition_service is None:
            raise RuntimeError("expedition_service is required for death respawn")
        return await self.expedition_service.respawn(char_id=character_id)

    async def resolve_starter_rift_death_context(
        self,
        session_doc: CharacterSessionDocumentDTO,
    ) -> dict[str, Any] | None:
        if self.rift_runtime is None:
            return None
        rift_session_id = session_doc.sessions.rift_session_id
        rift_instance_id = session_doc.sessions.rift_instance_id
        if not rift_session_id or not rift_instance_id:
            return None

        try:
            instance = await self.rift_runtime.require_instance(rift_instance_id)
            setting = _object_mapping(_read_field(instance, "setting"))
            population_context = _object_mapping(_read_field(instance, "population_context"))
            setting_key = str(setting.get("setting_key") or population_context.get("setting_key") or "")
            if setting_key != "starter_rift":
                return None
            run_session = await self.rift_runtime.require_run_session(rift_session_id)
        except Exception:
            logger.bind(
                char_id=session_doc.char_id,
                rift_session_id=rift_session_id,
                rift_instance_id=rift_instance_id,
            ).exception("StarterRiftDeathContextResolveFailed")
            return None

        return {
            "rift_key": setting_key,
            "rift_session_id": rift_session_id,
            "rift_instance_id": rift_instance_id,
            "current_node_id": _read_field(run_session, "current_node_id"),
            "active_encounter_id": _read_field(run_session, "active_encounter_id"),
            "death_run_id": session_doc.sessions.death_run_id,
            "attributes_before": session_doc.attributes.model_dump(mode="json"),
            "vitals_before": session_doc.vitals.model_dump(mode="json"),
            "metrics_before": session_doc.metrics.model_dump(mode="json"),
        }

    async def reset_starter_rift_character(
        self,
        character_id: int,
        *,
        user_id: UUID,
        starter_context: dict[str, Any],
        respawn_result: dict[str, Any],
    ) -> dict[str, Any]:
        if self.starter_reset_integration is None:
            raise RuntimeError("starter_reset_integration is required to reset starter rift character")

        previous_attempt_count = _int_or_zero(starter_context.get("attempt_count"))
        attempt_index = previous_attempt_count + 1
        seed = _starter_rift_reset_seed(
            character_id=character_id,
            respawn_result=respawn_result,
            attempt_index=attempt_index,
        )
        reset_result = await self.starter_reset_integration.reset_character_to_starting_imprint(
            user_id=user_id,
            character_id=character_id,
            seed=seed,
        )
        return {
            **reset_result,
            "attempt_index": attempt_index,
            "reset_seed": seed,
            "starter_context": starter_context,
        }

    async def claim_post_combat_loot(self, character_id: int, corpse_ids: list[str]) -> dict[str, Any]:
        if self.loot_manager is None:
            raise RuntimeError("loot_manager is required for post-combat loot")
        from src.backend.features.loot.integrations.loot_integration import LootIntegration
        from src.backend.features.loot.services.loot_service import LootService

        integration = LootIntegration(self.loot_manager)
        service = LootService(integration)
        requested = [str(corpse_id) for corpse_id in corpse_ids if corpse_id]
        session_doc = await self._active_session_document(character_id)
        post_combat = _post_combat(session_doc)
        target_state = _post_loot_target_state(post_combat)
        enqueued = 0
        for corpse_id in requested:
            claim = await service.claim_all(character_id, [corpse_id])
            if not claim.instance_ids and not claim.resource_deltas:
                continue
            if self.loot_arq is None:
                raise RuntimeError("loot_arq is required for post-combat loot claim")
            await self.loot_arq.enqueue_job(
                "loot_claim_task",
                {
                    "char_id": character_id,
                    "corpse_id": corpse_id,
                    "instance_ids": claim.instance_ids,
                    "resource_deltas": claim.resource_deltas,
                },
            )
            enqueued += 1

        if self.character_sessions is not None:
            await self.character_sessions.patch_fields(
                character_id,
                {
                    "$.state": target_state,
                    "$.prev_state": CoreDomain.LOOT.value,
                    "$.sessions.post_combat": None,
                },
            )
            await self.character_sessions.mark_dirty(
                character_id,
                reason="post_combat_loot_claimed",
                paths=["$.prev_state", "$.sessions.post_combat", "$.state"],
            )
        if target_state == CoreDomain.RIFT.value:
            await self._apply_rift_combat_result(session_doc, post_combat=post_combat)
        return {
            "status": "loot_claim_queued",
            "corpse_ids": requested,
            "queued_claims": enqueued,
            "target_state": target_state,
            "post_combat": post_combat,
        }

    async def _active_session_document(self, character_id: int) -> dict[str, Any] | None:
        if self.character_sessions is None or not hasattr(self.character_sessions, "get_session"):
            return None
        document = await self.character_sessions.get_session(character_id)
        return document if isinstance(document, dict) else None

    async def _apply_rift_combat_result(
        self,
        session_doc: dict[str, Any] | None,
        *,
        post_combat: dict[str, Any],
    ) -> None:
        if self.rift_runtime is None:
            return
        sessions = session_doc.get("sessions") if isinstance(session_doc, dict) else {}
        sessions = sessions if isinstance(sessions, dict) else {}
        loot_context = dict(post_combat.get("loot_context") or {})
        rift_session_id = str(sessions.get("rift_session_id") or loot_context.get("rift_session_id") or "")
        if not rift_session_id:
            return
        apply_combat_result = getattr(self.rift_runtime, "apply_combat_result", None)
        if apply_combat_result is None:
            await self.rift_runtime.clear_run_active_encounter(rift_session_id)
            return
        await apply_combat_result(
            combat_id=str(post_combat.get("combat_id") or ""),
            result="victory",
            rift_session_id=rift_session_id,
            rift_instance_id=str(sessions.get("rift_instance_id") or loot_context.get("rift_instance_id") or ""),
            event_scope=str(loot_context.get("rift_event_scope") or ""),
            travel_id=str(loot_context.get("rift_travel_id") or ""),
            event_key=str(loot_context.get("rift_event_key") or ""),
            participant_ref=str(sessions.get("participant_ref") or ""),
        )

    async def reconcile_stale_combat_active_session(
        self,
        character_id: int,
        *,
        persistent_state: CoreDomain | str,
        previous_state: CoreDomain | str | None,
    ) -> None:
        if self.character_sessions is None:
            return

        state_value = self._state_value(persistent_state) or CoreDomain.EXPLORATION.value
        previous_value = self._state_value(previous_state)
        await self.character_sessions.patch_fields(
            character_id,
            {
                "$.state": state_value,
                "$.prev_state": previous_value,
                "$.sessions.combat_id": None,
            },
        )
        await self.character_sessions.mark_dirty(
            character_id,
            reason="stale_combat_session_reconciled",
            paths=["$.prev_state", "$.sessions.combat_id", "$.state"],
        )
        logger.bind(char_id=character_id, state=state_value, previous_state=previous_value).warning(
            "GameSessionStaleCombatActiveSessionReconciled"
        )

    async def _persist_active_session_snapshot(self, character_id: int, document: dict[str, object]) -> None:
        if self.character_repo is None:
            return
        try:
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
        except Exception:
            logger.bind(char_id=character_id).exception("GameSessionActiveSessionSnapshotInvalid")
            return

        synced = await self.character_repo.sync_active_session_snapshot(character_id, session_doc)
        if synced is None:
            logger.bind(char_id=character_id).warning("GameSessionActiveSessionSnapshotSyncSkipped")

    async def resume_or_initialize_scenario(
        self,
        char_id: int,
        *,
        quest_key: str,
        source: str,
        previous_state: CoreDomain = CoreDomain.LOBBY,
    ) -> ScenarioPayloadDTO:
        if self.scenario_service is None:
            raise RuntimeError("scenario_service is required to resume or initialize scenario")
        try:
            payload = await self.scenario_service.resume(char_id)
        except ScenarioSessionNotFound:
            payload = await self.scenario_service.initialize(char_id, quest_key, source=source)
            await self.set_character_state(char_id, CoreDomain.SCENARIO, previous_state=previous_state)

        payload.extra_data = {
            **(payload.extra_data or {}),
            "char_id": char_id,
            "quest_key": (payload.extra_data or {}).get("quest_key", quest_key),
        }
        logger.bind(char_id=char_id, node_key=payload.node_key).info("GameSessionScenarioPayloadResolved")
        return payload

    async def set_character_state(
        self,
        char_id: int,
        state: CoreDomain,
        *,
        previous_state: CoreDomain | str | None = None,
    ) -> None:
        if self.character_repo is None:
            return
        updated = await self.character_repo.set_character_state(
            char_id,
            state.value,
            prev_game_stage=self._state_value(previous_state),
        )
        if not updated:
            logger.bind(char_id=char_id).warning("GameSessionPersistentStateUpdateSkipped")
            return

        await self.character_repo.commit()

    @staticmethod
    def _state_value(state: CoreDomain | str | None) -> str | None:
        if state is None:
            return None
        return state.value if isinstance(state, CoreDomain) else state


def _post_combat(session_doc: dict[str, Any] | None) -> dict[str, Any]:
    sessions = session_doc.get("sessions") if isinstance(session_doc, dict) else {}
    value = sessions.get("post_combat") if isinstance(sessions, dict) else None
    return dict(value) if isinstance(value, dict) else {}


def _post_loot_target_state(post_combat: dict[str, Any]) -> str:
    loot_context = dict(post_combat.get("loot_context") or {})
    raw = post_combat.get("return_state") or loot_context.get("return_state")
    if raw is None and str(post_combat.get("target_state") or "") != CoreDomain.LOOT.value:
        raw = post_combat.get("target_state")
    try:
        return CoreDomain(str(raw)).value if raw else CoreDomain.EXPLORATION.value
    except ValueError:
        return CoreDomain.EXPLORATION.value


def _read_field(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _object_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _starter_rift_reset_seed(
    *,
    character_id: int,
    respawn_result: dict[str, Any],
    attempt_index: int,
) -> str:
    run_id = str(respawn_result.get("run_id") or "no-run")
    return f"starter-rift-reset:{character_id}:{run_id}:{attempt_index}"


def _int_or_zero(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
