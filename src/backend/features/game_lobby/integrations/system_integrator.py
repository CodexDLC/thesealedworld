from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, cast

from loguru import logger
from sqlalchemy.exc import IntegrityError

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
from src.backend.features.character.services import StartingImprintBuild, StartingImprintService
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO, ItemOriginRefDTO, ItemPlacementRefDTO
from src.backend.features.items.integrations import ItemPersistenceIntegration
from src.backend.features.items.repositories import ItemInstanceRepository
from src.backend.features.items.services import ItemCatalogService, ItemGenerationService
from src.shared.enums import CoreDomain
from src.shared.enums.skill_enums import SkillProgressState
from src.shared.schemas import ScenarioPayloadDTO

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.backend.core.bus import GameEventProducer
    from src.backend.features.character.repositories import (
        CharacterAttributesRepository,
        CharacterProgressionRepository,
        SkillRepository,
        SymbioteRepository,
    )
    from src.backend.features.expedition import CharacterExpeditionRepository
    from src.backend.features.inventory.repositories.items import InventoryItemRepository
    from src.backend.features.rift.integrations import RiftRuntimeIntegration
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager, GameSessionLockManager
    from src.backend.infrastructure.game_lobby.managers import StartingImprintDistributionManager
    from src.backend.infrastructure.inventory.managers import InventorySessionManager


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
        progression_repo: CharacterProgressionRepository | None = None,
        symbiote_repo: SymbioteRepository | None = None,
        expedition_repo: CharacterExpeditionRepository | None = None,
        inventory_repo: InventoryItemRepository | None = None,
        item_persistence: ItemPersistenceIntegration | None = None,
        inventory_sessions: InventorySessionManager | None = None,
        scenario_service: Any | None = None,
        db_session: AsyncSession | None = None,
        character_sessions: CharacterSessionManager,
        game_session_lock: GameSessionLockManager | None = None,
        events: GameEventProducer | None = None,
        starting_imprint_distribution: StartingImprintDistributionManager | None = None,
        rift_runtime: RiftRuntimeIntegration | None = None,
    ) -> None:
        if character_repo is None:
            if db_session is None:
                raise ValueError("character_repo or db_session is required")
            character_repo = CharacterRepository(db_session)
        self.character_repo = character_repo
        self.attributes_repo = attributes_repo
        self.skill_repo = skill_repo
        self.progression_repo = progression_repo
        self.symbiote_repo = symbiote_repo
        self.expedition_repo = expedition_repo
        self.inventory_repo = inventory_repo
        self.item_persistence = item_persistence
        if self.item_persistence is None and db_session is not None:
            self.item_persistence = ItemPersistenceIntegration(ItemInstanceRepository(db_session))
        self.inventory_sessions = inventory_sessions
        self.character_sessions = character_sessions
        self.game_session_lock = game_session_lock
        self.events = events
        self.starting_imprint_distribution = starting_imprint_distribution
        self.scenario_service = scenario_service
        self.rift_runtime = rift_runtime

    async def _release_session_lock(self, char_id: int) -> None:
        """Best-effort release of the single-session lock; never raises."""
        if self.game_session_lock is None:
            return
        try:
            await self.game_session_lock.release(char_id)
        except Exception:  # noqa: BLE001
            logger.bind(char_id=char_id).warning("GameSessionLockReleaseFailed")

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

    async def count_all_characters(self) -> int:
        return await self._characters().count_all()

    async def create_character(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        name_key: str,
        gender: CharacterGender,
        avatar_url: str,
        game_stage: str,
        prev_game_stage: str,
        location_id: str,
    ) -> CreatedLobbyCharacter:
        created_at = datetime.now(UTC)
        try:
            character = await self._characters().create_with_defaults(
                user_id=user_id,
                name=name,
                name_key=name_key,
                gender=str(gender),
                avatar_url=avatar_url,
                game_stage=game_stage,
                prev_game_stage=prev_game_stage,
                location_id=location_id,
            )
            char_id = character.character_id
            await self._characters().commit()
        except IntegrityError as exc:
            await self._characters().rollback()
            if _is_character_name_key_violation(exc):
                raise BusinessLogicException("Имя уже занято") from exc
            raise
        logger.bind(char_id=char_id, user_id=str(user_id)).info("CharacterPersisted")

        return CreatedLobbyCharacter(
            character_id=char_id,
            user_id=user_id,
            name=name,
            gender=gender,
            avatar_url=avatar_url,
            created_at=created_at,
            location_id=location_id,
        )

    async def character_name_exists(self, name_key: str) -> bool:
        return await self._characters().exists_by_name_key(name_key)

    async def create_active_session(self, character: CreatedLobbyCharacter) -> None:
        if self.skill_repo is not None:
            state_integrator = CharacterStateIntegrator(
                character_sessions=self.character_sessions,
                character_repo=self.character_repo,
                skill_repo=self.skill_repo,
                progression_repo=self.progression_repo,
                expedition_repo=self.expedition_repo,
                inventory_repo=self.inventory_repo,
            )
            await state_integrator.bootstrap_active_session(character.user_id, character.character_id)
            return

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

    async def materialize_starting_imprint(
        self,
        character: CreatedLobbyCharacter,
        *,
        seed: str | None = None,
        imprint_key: str | None = None,
        exclude_imprint_key: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_starting_imprint_dependencies()
        assert self.attributes_repo is not None
        assert self.skill_repo is not None
        assert self.item_persistence is not None
        service = StartingImprintService()
        if imprint_key:
            build = service.build(imprint_key)
        elif self.starting_imprint_distribution is not None:
            exclude_keys = [exclude_imprint_key] if exclude_imprint_key else None
            selected_imprint_key = await self.starting_imprint_distribution.select_and_record(
                user_id=character.user_id,
                seed=seed,
                imprint_keys=service.available_keys(),
                exclude_keys=exclude_keys,
            )
            build = service.build(selected_imprint_key)
        else:
            build = service.build_random(seed=seed)
        char_id = character.character_id

        await self.attributes_repo.upsert_attributes(char_id, build.attributes)
        if self.progression_repo is not None:
            await self.progression_repo.set_free_xp(char_id, 0.0)
        await self._materialize_starting_skills(char_id, build)
        item_ids = await self._materialize_starting_items(char_id, build, seed=seed)
        self._expire_identity_map()
        await self.character_repo.commit()
        logger.bind(
            char_id=char_id,
            imprint_key=build.imprint_key,
            item_count=len(item_ids),
            skill_count=len(build.skill_keys),
        ).info("StartingImprintMaterialized")
        return {
            "imprint_key": build.imprint_key,
            "title": build.title,
            "item_ids": item_ids,
            "skill_keys": list(build.skill_keys),
            "attributes": dict(build.attributes),
        }

    async def reset_character_to_starting_imprint(
        self,
        *,
        user_id: uuid.UUID,
        character_id: int,
        seed: str | None = None,
        imprint_key: str | None = None,
    ) -> dict[str, Any]:
        character = await self._characters().get_by_id_and_user_id(character_id, user_id)
        if character is None:
            raise BusinessLogicException("Персонаж недоступен")

        exclude_imprint_key = None
        if self.attributes_repo is not None:
            attrs_list = await self.attributes_repo.get_attributes_batch([character_id])
            if attrs_list:
                char_attrs = attrs_list[0]
                from src.backend.features.character.resources.starting_imprints import (
                    ATTRIBUTE_KEYS,
                    STARTING_IMPRINTS,
                )

                for key, definition in STARTING_IMPRINTS.items():
                    def_attrs = dict(definition.attribute_values)
                    match = True
                    for attr_name in ATTRIBUTE_KEYS:
                        if getattr(char_attrs, attr_name, None) != def_attrs.get(attr_name):
                            match = False
                            break
                    if match:
                        exclude_imprint_key = key
                        break

        avatar_url = _default_avatar_url(character.gender)
        character.avatar_url = avatar_url
        character.game_stage = CoreDomain.EXPLORATION.value
        character.prev_game_stage = CoreDomain.DEATH.value
        character.location_id = "52_52"
        character.prev_location_id = None
        character.vitals_snapshot = None
        character.active_sessions = {}
        character.respawn_anchor_location_id = "52_52"

        reset_character = CreatedLobbyCharacter(
            character_id=character.character_id,
            user_id=character.user_id,
            name=character.name,
            gender=cast("CharacterGender", character.gender),
            avatar_url=avatar_url,
            created_at=character.created_at,
            location_id="52_52",
        )

        await self.cleanup_runtime(character_id, clear_inventory_session=True)
        transferred_items = 0
        if self.item_persistence is not None:
            transferred_items = await self.item_persistence.transfer_deleted_character_items_to_system(character_id)
        if self.skill_repo is not None:
            await self.skill_repo.delete_by_character_id(character_id)

        starting_imprint = await self.materialize_starting_imprint(
            reset_character,
            seed=seed,
            imprint_key=imprint_key,
            exclude_imprint_key=exclude_imprint_key,
        )
        await self.bootstrap_active_character(user_id=user_id, character_id=character_id)
        logger.bind(
            char_id=character_id,
            user_id=str(user_id),
            imprint_key=starting_imprint.get("imprint_key"),
            transferred_items=transferred_items,
        ).info("LobbyCharacterResetToStartingImprint")
        return {
            "status": "reset",
            "character_id": character_id,
            "starting_imprint": starting_imprint,
            "transferred_item_count": transferred_items,
        }

    def _ensure_starting_imprint_dependencies(self) -> None:
        missing = [
            name
            for name, dependency in {
                "attributes_repo": self.attributes_repo,
                "skill_repo": self.skill_repo,
                "item_persistence": self.item_persistence,
            }.items()
            if dependency is None
        ]
        if missing:
            raise RuntimeError(f"Starting imprint materialization is not configured: missing={', '.join(missing)}")

    async def _materialize_starting_skills(self, char_id: int, build: StartingImprintBuild) -> None:
        if self.skill_repo is None:
            raise RuntimeError("Starting imprint skill materialization is not configured")
        rows = [
            {
                "character_id": char_id,
                "skill_key": skill_key,
                "total_xp": float(xp),
                "is_unlocked": True,
                "progress_state": SkillProgressState.PLUS,
            }
            for skill_key, xp in build.skill_xp.items()
        ]
        await self.skill_repo.upsert_progress_rows(rows)

    async def _materialize_starting_items(
        self,
        char_id: int,
        build: StartingImprintBuild,
        *,
        seed: str | None = None,
    ) -> list[str]:
        item_generation = ItemGenerationService(self.item_persistence)
        catalog = ItemCatalogService.load_default()
        item_ids: list[str] = []
        occupied_slots: set[str] = set()
        for index, base_id in enumerate(build.item_base_ids, start=1):
            base = catalog.get_base_item(base_id)
            if base is None:
                raise RuntimeError(f"Starting imprint item base is missing: {base_id}")
            slot = self._starting_item_slot(base, occupied_slots)
            occupied_slots.add(slot)
            result = await item_generation.generate_mechanical(
                ItemGenerationRequestDTO(
                    base_id=base_id,
                    target_slot=slot,
                    rarity_tier=0,
                    source="character_creation:starting_imprint",
                    char_id=char_id,
                    request_ai_text=False,
                    placement_ref=ItemPlacementRefDTO(
                        holder_type="character",
                        holder_id=str(char_id),
                        storage_type="equipped",
                        slot=slot,
                    ),
                    origin_ref=ItemOriginRefDTO(
                        origin_type="system",
                        origin_ref=f"starting_imprint:{build.imprint_key}",
                        seed=f"{seed or build.imprint_key}:{char_id}:{index}:{base_id}",
                    ),
                    source_context={
                        "starting_imprint": True,
                        "imprint_key": build.imprint_key,
                        "imprint_title": build.title,
                        "combat_style": build.combat_style,
                        "armor_pack": build.armor_pack,
                        "utility_pack": build.utility_pack,
                    },
                    return_item=False,
                )
            )
            item_ids.extend(result.item_ids)
        return item_ids

    @staticmethod
    def _starting_item_slot(base, occupied_slots: set[str]) -> str:
        base_slot = str(base.slot)
        if base_slot not in occupied_slots:
            return base_slot
        for extra_slot in base.extra_slots:
            slot = str(extra_slot)
            if slot not in occupied_slots:
                return slot
        return base_slot

    def _expire_identity_map(self) -> None:
        session = getattr(self.character_repo, "session", None)
        expire_all = getattr(session, "expire_all", None)
        if callable(expire_all):
            expire_all()

    async def bootstrap_active_character(
        self,
        *,
        user_id: uuid.UUID,
        character_id: int,
    ) -> CharacterSessionDocumentDTO:
        if self.skill_repo is None:
            raise RuntimeError("skill_repo is required for lobby character bootstrap")

        if await self.character_sessions.exists(character_id):
            document = await self.character_sessions.get_session(character_id)
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
            if session_doc.user_id != user_id:
                raise BusinessLogicException("Персонаж недоступен")
            logger.bind(user_id=str(user_id), char_id=character_id, state=session_doc.state).info(
                "LobbyActiveCharacterSessionReused"
            )
            return session_doc

        state_integrator = CharacterStateIntegrator(
            character_sessions=self.character_sessions,
            character_repo=self.character_repo,
            skill_repo=self.skill_repo,
            progression_repo=self.progression_repo,
            expedition_repo=self.expedition_repo,
            inventory_repo=self.inventory_repo,
        )
        session_doc = await state_integrator.bootstrap_active_session(user_id, character_id)
        logger.bind(user_id=str(user_id), char_id=character_id).info("LobbyActiveCharacterSessionBootstrapped")
        return session_doc

    async def release_active_character(self, *, user_id: uuid.UUID, character_id: int) -> None:
        character = await self._characters().get_by_id_and_user_id(character_id, user_id)
        if character is None:
            raise BusinessLogicException("Персонаж недоступен")
        if not await self.character_sessions.exists(character_id):
            return
        if self.attributes_repo is None or self.skill_repo is None:
            raise RuntimeError("attributes_repo and skill_repo are required for lobby character release")

        sync = CharacterSystemIntegrator(
            character_sessions=self.character_sessions,
            character_repo=self.character_repo,
            attributes_repo=self.attributes_repo,
            skill_repo=self.skill_repo,
            progression_repo=self.progression_repo,
            expedition_repo=self.expedition_repo,
        )
        await sync.sync_active_session(character_id)
        await self.character_sessions.delete_session(character_id)
        await self._release_session_lock(character_id)
        await self._characters().commit()
        logger.bind(user_id=str(user_id), char_id=character_id).info("LobbyActiveCharacterSessionReleased")

    async def initialize_starting_scenario(
        self,
        char_id: int,
        quest_key: str,
        *,
        source: str,
        npc_key: str | None = None,
    ) -> ScenarioPayloadDTO:
        if self.events is None:
            raise RuntimeError("events bus is required for scenario initialization")
        response = await self.events.request(
            "scenario.start_requested",
            {"char_id": char_id, "quest_key": quest_key, "source": source, "npc_key": npc_key or ""},
            timeout=30.0,
        )
        if not isinstance(response, dict) or response.get("status") != "ok":
            raise RuntimeError(f"Scenario initialization failed: {response!r}")
        return ScenarioPayloadDTO(**response["payload"])

    async def cleanup_runtime(self, char_id: int, *, clear_inventory_session: bool = False) -> None:
        document = await self._active_character_document(char_id)
        if self.events is not None:
            await self.events.request(
                "scenario.cleanup_requested",
                {"char_id": char_id},
                timeout=15.0,
            )
        elif self.scenario_service is not None and hasattr(self.scenario_service, "cleanup"):
            await self.scenario_service.cleanup(char_id)
        await self._abandon_active_rift(char_id, document)
        if clear_inventory_session:
            await self._clear_inventory_session(char_id)
        await self.character_sessions.delete_session(char_id)
        await self._release_session_lock(char_id)

    async def _active_character_document(self, char_id: int) -> dict[str, Any] | None:
        getter = getattr(self.character_sessions, "get_session", None)
        if getter is None:
            return None
        with suppress(Exception):
            document = await getter(char_id)
            return document if isinstance(document, dict) else None
        return None

    async def _clear_inventory_session(self, char_id: int) -> None:
        if self.inventory_sessions is None:
            return
        with suppress(Exception):
            await self.inventory_sessions.delete(char_id)

    async def _abandon_active_rift(self, char_id: int, document: dict[str, Any] | None) -> None:
        if self.rift_runtime is None or not isinstance(document, dict):
            return
        sessions = document.get("sessions")
        sessions = sessions if isinstance(sessions, dict) else {}
        rift_session_id = str(sessions.get("rift_session_id") or "")
        rift_instance_id = str(sessions.get("rift_instance_id") or "")
        if not rift_session_id or not rift_instance_id:
            return
        try:
            await self.rift_runtime.abandon_run_for_deleted_character(
                rift_session_id=rift_session_id,
                rift_instance_id=rift_instance_id,
                char_id=char_id,
            )
        except Exception:  # noqa: BLE001
            logger.bind(char_id=char_id, rift_session_id=rift_session_id).exception("LobbyRiftCleanupFailed")

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
            logger.bind(
                user_id=str(user_id),
                selected_char_id=selected_character_id,
                released_char_id=character_id,
            ).info("LobbyPreviousActiveCharacterSessionReleased")

        if persisted_any:
            await self._characters().commit()

    async def _persist_active_session_snapshot(self, character_id: int, document: dict[str, object]) -> None:
        if self.attributes_repo is not None and self.skill_repo is not None:
            sync = CharacterSystemIntegrator(
                character_sessions=self.character_sessions,
                character_repo=self.character_repo,
                attributes_repo=self.attributes_repo,
                skill_repo=self.skill_repo,
                progression_repo=self.progression_repo,
                expedition_repo=self.expedition_repo,
            )
            await sync.sync_active_session(character_id)
            return

        try:
            session_doc = CharacterSessionDocumentDTO.model_validate(document)
        except Exception:
            logger.bind(char_id=character_id).exception("LobbyActiveSessionSnapshotValidationFailed")
            return

        synced = await self._characters().sync_active_session_snapshot(character_id, session_doc)
        if synced is None:
            logger.bind(char_id=character_id).warning("LobbyActiveSessionSnapshotSyncSkipped")

    async def delete_owned_character(self, *, user_id: uuid.UUID, character_id: int, confirm_name: str) -> None:
        repo = self._characters()
        character = await repo.get_by_id_and_user_id(character_id, user_id)
        if character is None:
            raise BusinessLogicException("Персонаж недоступен")
        if character.name != confirm_name:
            raise BusinessLogicException("Имя подтверждения не совпадает")

        char_id = character.character_id
        await self.cleanup_runtime(char_id)
        if self.item_persistence is not None:
            transferred_count = await self.item_persistence.transfer_deleted_character_items_to_system(char_id)
            if transferred_count:
                logger.bind(char_id=char_id, item_count=transferred_count).info("LobbyDeletedCharacterItemsTransferred")
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
        await self._release_session_lock(char_id)
        with suppress(Exception):
            if self.item_persistence is not None:
                await self.item_persistence.transfer_deleted_character_items_to_system(char_id)
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
            raise BusinessLogicException("Персонаж недоступен")
        await self._characters().commit()


def _is_character_name_key_violation(exc: IntegrityError) -> bool:
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint_name == "uq_characters_name_key":
        return True
    return "uq_characters_name_key" in str(exc.orig)


def _default_avatar_url(gender: str | None) -> str:
    if gender == "female":
        return "/static/images/avatars/silhouette_f.webp"
    return "/static/images/avatars/silhouette_m.webp"
