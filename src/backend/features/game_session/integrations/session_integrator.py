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
    from src.backend.features.character.managers.session import CharacterSessionManager
    from src.backend.features.scenario.services import ScenarioService
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
            logger.info(
                "Released previous active character session: user_id={} selected_char_id={} released_char_id={}",
                user_id,
                selected_character_id,
                character_id,
            )

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
                logger.warning("Game session cold AC bootstrap failed: char_id={}", character_id, exc_info=True)
                return None

        try:
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
        except Exception:
            logger.warning("Game session hot AC validation failed: char_id={}", character_id, exc_info=True)
            return None

        if session_doc.user_id != user_id:
            logger.warning(
                "Game session hot AC ownership mismatch: char_id={} owner={} requested_by={}",
                character_id,
                session_doc.user_id,
                user_id,
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

    async def claim_post_combat_loot(self, character_id: int, corpse_ids: list[str]) -> dict[str, Any]:
        if self.loot_manager is None:
            raise RuntimeError("loot_manager is required for post-combat loot")
        from src.backend.features.loot.integrations.loot_integration import LootIntegration
        from src.backend.features.loot.services.loot_service import LootService

        integration = LootIntegration(self.loot_manager)
        service = LootService(integration)
        requested = [str(corpse_id) for corpse_id in corpse_ids if corpse_id]
        enqueued = 0
        for corpse_id in requested:
            claim = await service.claim_all(character_id, [corpse_id])
            if not claim.instance_ids and not claim.resource_deltas:
                continue
            if self.loot_arq is not None:
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
                    "$.state": CoreDomain.EXPLORATION.value,
                    "$.prev_state": CoreDomain.LOOT.value,
                    "$.sessions.post_combat": None,
                },
            )
            await self.character_sessions.mark_dirty(
                character_id,
                reason="post_combat_loot_claimed",
                paths=["$.prev_state", "$.sessions.post_combat", "$.state"],
            )
        return {"status": "loot_claim_queued", "corpse_ids": requested, "queued_claims": enqueued}

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
        logger.warning(
            "Reconciled stale hot combat session from persistent state: char_id={} state={} prev_state={}",
            character_id,
            state_value,
            previous_value,
        )

    async def _persist_active_session_snapshot(self, character_id: int, document: dict[str, object]) -> None:
        if self.character_repo is None:
            return
        try:
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
        except Exception:
            logger.warning(
                "Skipping invalid active session snapshot before release: char_id={}", character_id, exc_info=True
            )
            return

        synced = await self.character_repo.sync_active_session_snapshot(character_id, session_doc)
        if synced is None:
            logger.warning("Skipping active session snapshot sync; character missing: char_id={}", character_id)

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
        logger.info("Game session scenario payload resolved: char_id={} node={}", char_id, payload.node_key)
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
            logger.warning("Game session persistent state update skipped; character missing: char_id={}", char_id)
            return

        await self.character_repo.commit()

    @staticmethod
    def _state_value(state: CoreDomain | str | None) -> str | None:
        if state is None:
            return None
        return state.value if isinstance(state, CoreDomain) else state
