from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger

from src.backend.core.exceptions import BusinessLogicException
from src.backend.features.character.integrations import CharacterStateIntegrator, CharacterSystemIntegrator
from src.backend.features.character.repositories import CharacterRepository
from src.backend.features.character.schemas.session import (
    CharacterGender,
    CharacterSessionAttributesDTO,
    CharacterSessionBioDTO,
    CharacterSessionDocumentDTO,
    CharacterSessionLocationDTO,
    CharacterSessionSymbioteDTO,
)
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.shared.enums import CoreDomain
from src.shared.schemas import ScenarioPayloadDTO

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.core.bus import GameEventProducer
    from src.backend.features.character.managers import CharacterSessionManager
    from src.backend.features.character.repositories import CharacterAttributesRepository, SkillRepository
    from src.backend.features.inventory.repositories.items import InventoryItemRepository


@dataclass(frozen=True, slots=True)
class LobbyCharacterSummary:
    character_id: int
    name: str
    avatar_url: str | None
    status: str
    presence_status: Literal["online", "offline"] = "offline"


@dataclass(frozen=True, slots=True)
class CreatedLobbyCharacter:
    character_id: int
    user_id: uuid.UUID
    name: str
    gender: CharacterGender
    avatar_url: str
    created_at: datetime
    location_id: str


class GameLobbyIntegration:
    def __init__(
        self,
        *,
        character_repo: CharacterRepository | None = None,
        attributes_repo: CharacterAttributesRepository | None = None,
        skill_repo: SkillRepository | None = None,
        inventory_repo: InventoryItemRepository | None = None,
        item_persistence: ItemPersistenceIntegration | None = None,
        scenario_service: Any | None = None,
        db_session: AsyncSession | None = None,
        character_sessions: CharacterSessionManager,
        events: GameEventProducer | None = None,
    ) -> None:
        if character_repo is None:
            if db_session is None:
                raise ValueError("character_repo or db_session is required")
            character_repo = CharacterRepository(db_session)
        self.character_repo = character_repo
        self.attributes_repo = attributes_repo
        self.skill_repo = skill_repo
        self.inventory_repo = inventory_repo
        self.item_persistence = item_persistence
        if self.item_persistence is None and db_session is not None:
            self.item_persistence = ItemPersistenceIntegration(ItemInstanceRepository(db_session))
        self.character_sessions = character_sessions
        self.events = events
        self.scenario_service = scenario_service

    def _characters(self) -> CharacterRepository:
        return self.character_repo

    async def list_user_characters(self, user_id: uuid.UUID) -> list[LobbyCharacterSummary]:
        characters = await self._characters().get_by_user_id(user_id)
        return [
            LobbyCharacterSummary(
                character_id=character.character_id,
                name=character.name,
                avatar_url=character.avatar_url,
                status=str(character.game_stage or "lobby"),
                presence_status="offline",
            )
            for character in characters
        ]

    async def count_user_characters(self, user_id: uuid.UUID) -> int:
        return await self._characters().count_by_user_id(user_id)

    async def create_character(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        gender: CharacterGender,
        avatar_url: str,
        game_stage: str,
        prev_game_stage: str,
        location_id: str,
    ) -> CreatedLobbyCharacter:
        created_at = datetime.now(UTC)
        character = await self._characters().create_with_defaults(
            user_id=user_id,
            name=name,
            gender=str(gender),
            avatar_url=avatar_url,
            game_stage=game_stage,
            prev_game_stage=prev_game_stage,
            location_id=location_id,
        )
        char_id = character.character_id
        await self._characters().commit()
        logger.info("Character persisted: char_id={} user_id={}", char_id, user_id)

        return CreatedLobbyCharacter(
            character_id=char_id,
            user_id=user_id,
            name=name,
            gender=gender,
            avatar_url=avatar_url,
            created_at=created_at,
            location_id=location_id,
        )

    async def create_active_session(self, character: CreatedLobbyCharacter) -> None:
        session_payload = CharacterSessionDocumentDTO(
            char_id=character.character_id,
            user_id=character.user_id,
            state=CoreDomain.LOBBY,
            prev_state=None,
            bio=CharacterSessionBioDTO(
                name=character.name,
                gender=character.gender,
                avatar=character.avatar_url,
                created_at=character.created_at,
            ),
            location=CharacterSessionLocationDTO(current=character.location_id),
            attributes=CharacterSessionAttributesDTO(),
            symbiote=CharacterSessionSymbioteDTO(),
            updated_at=datetime.now(UTC),
        ).model_dump(mode="json")

        await self.character_sessions.create_session(character.character_id, session_payload)

    async def bootstrap_active_character(
        self,
        *,
        user_id: uuid.UUID,
        character_id: int,
    ) -> CharacterSessionDocumentDTO:
        if self.skill_repo is None:
            raise RuntimeError("skill_repo is required for lobby character bootstrap")

        if await self.character_sessions.exists(character_id):
            await self.release_active_character(user_id=user_id, character_id=character_id)
            await self.cleanup_runtime(character_id)

        state_integrator = CharacterStateIntegrator(
            character_sessions=self.character_sessions,
            character_repo=self.character_repo,
            skill_repo=self.skill_repo,
            inventory_repo=self.inventory_repo,
        )
        session_doc = await state_integrator.bootstrap_active_session(user_id, character_id)
        logger.info("Lobby bootstrapped active character session: user_id={} char_id={}", user_id, character_id)
        return session_doc

    async def release_active_character(self, *, user_id: uuid.UUID, character_id: int) -> None:
        character = await self._characters().get_by_id_and_user_id(character_id, user_id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")
        if not await self.character_sessions.exists(character_id):
            return
        if self.attributes_repo is None or self.skill_repo is None:
            raise RuntimeError("attributes_repo and skill_repo are required for lobby character release")

        sync = CharacterSystemIntegrator(
            character_sessions=self.character_sessions,
            character_repo=self.character_repo,
            attributes_repo=self.attributes_repo,
            skill_repo=self.skill_repo,
        )
        await sync.sync_active_session(character_id)
        await self.character_sessions.delete_session(character_id)
        await self._characters().commit()
        logger.info("Lobby released active character session: user_id={} char_id={}", user_id, character_id)

    async def initialize_starting_scenario(
        self,
        char_id: int,
        quest_key: str,
        *,
        source: str,
    ) -> ScenarioPayloadDTO:
        if self.events is None:
            raise RuntimeError("events bus is required for scenario initialization")
        response = await self.events.request(
            "scenario.start_requested",
            {"char_id": char_id, "quest_key": quest_key, "source": source},
            timeout=30.0,
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Scenario initialization failed: {response!r}")
        return ScenarioPayloadDTO(**response["payload"])

    async def cleanup_runtime(self, char_id: int) -> None:
        if self.events is not None:
            await self.events.request(
                "scenario.cleanup_requested",
                {"char_id": char_id},
                timeout=15.0,
            )
        elif self.scenario_service is not None and hasattr(self.scenario_service, "cleanup"):
            await self.scenario_service.cleanup(char_id)
        await self.character_sessions.delete_session(char_id)

    async def release_other_active_sessions(self, user_id: uuid.UUID, selected_character_id: int) -> None:
        characters = await self._characters().get_by_user_id(user_id)
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
            await self.cleanup_runtime(character_id)
            logger.info(
                "Lobby released previous active character session: user_id={} selected_char_id={} released_char_id={}",
                user_id,
                selected_character_id,
                character_id,
            )

        if persisted_any:
            await self._characters().commit()

    async def _persist_active_session_snapshot(self, character_id: int, document: dict[str, object]) -> None:
        if self.attributes_repo is not None and self.skill_repo is not None:
            sync = CharacterSystemIntegrator(
                character_sessions=self.character_sessions,
                character_repo=self.character_repo,
                attributes_repo=self.attributes_repo,
                skill_repo=self.skill_repo,
            )
            await sync.sync_active_session(character_id)
            return

        try:
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
        except Exception:
            logger.warning("Lobby active session snapshot validation failed: char_id={}", character_id, exc_info=True)
            return

        synced = await self._characters().sync_active_session_snapshot(character_id, session_doc)
        if synced is None:
            logger.warning("Lobby active session snapshot sync skipped; character missing: char_id={}", character_id)

    async def delete_owned_character(self, *, user_id: uuid.UUID, character_id: int) -> None:
        repo = self._characters()
        character = await repo.get_by_id_and_user_id(character_id, user_id)
        if character is None:
            raise BusinessLogicException("Character is unavailable")

        char_id = character.character_id
        await self.cleanup_runtime(char_id)
        if self.item_persistence is not None:
            transferred_count = await self.item_persistence.transfer_deleted_character_items_to_system(char_id)
            if transferred_count:
                logger.info(
                    "Lobby transferred deleted character item instances to system custody: char_id={} count={}",
                    char_id,
                    transferred_count,
                )
        await repo.delete(char_id)
        await repo.commit()

    async def cleanup_failed_character_creation(self, char_id: int) -> None:
        repo = self._characters()
        await repo.rollback()
        with suppress(Exception):
            if self.events is not None:
                await self.events.request(
                    "scenario.cleanup_requested",
                    {"char_id": char_id},
                    timeout=10.0,
                )
            elif self.scenario_service is not None and hasattr(self.scenario_service, "cleanup"):
                await self.scenario_service.cleanup(char_id)
        with suppress(Exception):
            await self.character_sessions.delete_session(char_id)
        with suppress(Exception):
            await repo.delete(char_id)

        await repo.commit()

    async def mark_character_entered_scenario(self, char_id: int) -> None:
        updated = await self._characters().set_character_state(
            char_id,
            CoreDomain.SCENARIO.value,
            prev_game_stage=CoreDomain.LOBBY.value,
        )
        if not updated:
            raise BusinessLogicException("Character is unavailable")
        await self._characters().commit()
