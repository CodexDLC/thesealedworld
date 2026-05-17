import uuid
from typing import Any

from loguru import logger as log
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.features.character.models import (
    Character,
    CharacterAttributes,
    CharacterProgression,
    CharacterSymbiote,
)
from src.backend.features.character.schemas.session import CharacterSessionDocumentDTO
from src.backend.infrastructure.inventory import ResourceWallet
from src.shared.schemas.character import CharacterReadDTO


class CharacterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_by_user_id(self, user_id: uuid.UUID) -> int:
        log.debug(f"CharacterRepository | action=count_by_user_id user_id={user_id}")
        stmt = select(func.count()).select_from(Character).where(Character.user_id == user_id)
        result = await self.session.scalar(stmt)
        return int(result or 0)

    async def save(self, character: Character) -> Character:
        log.debug(f"CharacterRepository | action=save character={character.name}")
        self.session.add(character)
        await self.session.flush()
        return character

    async def exists_by_name_key(self, name_key: str) -> bool:
        log.debug("CharacterRepository | action=exists_by_name_key name_key={}", name_key)
        stmt = select(Character.character_id).where(Character.name_key == name_key).limit(1)
        return await self.session.scalar(stmt) is not None

    async def create_with_defaults(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        name_key: str,
        gender: str,
        avatar_url: str,
        game_stage: str,
        prev_game_stage: str,
        location_id: str,
    ) -> Character:
        character = Character(
            user_id=user_id,
            name=name,
            name_key=name_key,
            gender=gender,
            avatar_url=avatar_url,
            game_stage=game_stage,
            prev_game_stage=prev_game_stage,
            location_id=location_id,
        )
        character.attributes = CharacterAttributes()
        character.progression = CharacterProgression()
        character.symbiote = CharacterSymbiote()
        character.wallet = ResourceWallet()
        return await self.save(character)

    async def flush(self) -> None:
        await self.session.flush()

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[Character]:
        log.debug(f"CharacterRepository | action=get_by_user_id user_id={user_id}")
        stmt = (
            select(Character).where(Character.user_id == user_id).order_by(Character.created_at, Character.character_id)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_by_id(self, character_id: int) -> Character | None:
        log.debug(f"CharacterRepository | action=get_by_id char_id={character_id}")
        stmt = select(Character).where(Character.character_id == character_id)
        return await self.session.scalar(stmt)

    async def get_by_id_and_user_id(self, character_id: int, user_id: uuid.UUID) -> Character | None:
        log.debug(f"CharacterRepository | action=get_by_id_and_user_id char_id={character_id} user_id={user_id}")
        stmt = (
            select(Character)
            .options(
                selectinload(Character.attributes),
                selectinload(Character.skill_progress),
                selectinload(Character.symbiote),
            )
            .where(Character.character_id == character_id, Character.user_id == user_id)
        )
        return await self.session.scalar(stmt)

    async def delete(self, character_id: int) -> None:
        log.warning(f"CharacterRepository | action=delete char_id={character_id}")
        await self.session.execute(delete(Character).where(Character.character_id == character_id))

    async def delete_owned(self, *, user_id: uuid.UUID, character_id: int) -> Character | None:
        character = await self.get_by_id_and_user_id(character_id, user_id)
        if character is None:
            return None
        await self.delete(character.character_id)
        return character

    async def set_character_state(
        self,
        character_id: int,
        game_stage: str,
        *,
        prev_game_stage: str | None = None,
        skip_if_same: bool = False,
        use_current_as_previous: bool = False,
    ) -> bool:
        character = await self.get_by_id(character_id)
        if character is None:
            return False
        current_stage = (character.game_stage or "").strip().lower()
        if skip_if_same and current_stage == game_stage:
            return True
        character.prev_game_stage = (
            current_stage if use_current_as_previous and prev_game_stage is None else prev_game_stage
        )
        character.game_stage = game_stage
        return True

    async def sync_active_session_snapshot(
        self,
        character_id: int,
        session_doc: CharacterSessionDocumentDTO,
    ) -> dict[str, Any] | None:
        character = await self.get_by_id(character_id)
        if character is None:
            return None

        character.game_stage = str(self._state_value(session_doc.state) or "")
        character.prev_game_stage = str(self._state_value(session_doc.prev_state) or "")
        character.location_id = session_doc.location.current
        character.prev_location_id = session_doc.location.prev
        character.vitals_snapshot = session_doc.vitals.model_dump(mode="json")
        character.active_sessions = {
            **session_doc.sessions.model_dump(mode="json"),
            "active_quest": session_doc.active_quest,
        }

        await self.session.flush()
        return {
            "state": character.game_stage,
            "location_id": character.location_id,
        }

    @staticmethod
    def _state_value(state: Any | None) -> str | None:
        if state is None:
            return None
        value = getattr(state, "value", state)
        return str(value)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def get_characters_batch(self, char_ids: list[int]) -> list[CharacterReadDTO]:
        log.debug(f"CharacterRepository | action=get_characters_batch count={len(char_ids)}")
        if not char_ids:
            return []

        stmt = select(Character).where(Character.character_id.in_(char_ids))
        try:
            result = await self.session.scalars(stmt)
            return [CharacterReadDTO.model_validate(character) for character in result.all()]
        except SQLAlchemyError as exc:
            log.exception(f"CharacterRepository | action=get_characters_batch status=failed error={exc}")
            raise
