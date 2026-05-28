from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.backend.features.character.models import Character
from src.backend.features.items.models import ItemInstance, ItemPlacement


class AdminPlayerReadRepository:
    def __init__(self, session: Any) -> None:
        self.session = session

    async def count_characters_for_user(self, user_id: UUID) -> int:
        total = await self.session.scalar(
            select(func.count()).select_from(Character).where(Character.user_id == user_id)
        )
        return int(total or 0)

    async def list_characters_for_user(self, user_id: UUID, *, limit: int, offset: int) -> list[Character]:
        result = await self.session.scalars(
            select(Character)
            .where(Character.user_id == user_id)
            .order_by(Character.created_at.desc().nulls_last(), Character.character_id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.all())

    async def get_character_detail(self, character_id: int) -> Character | None:
        return await self.session.scalar(
            select(Character)
            .options(
                selectinload(Character.attributes),
                selectinload(Character.skill_progress),
                selectinload(Character.progression),
            )
            .where(Character.character_id == character_id)
        )

    async def list_active_items(self, character_id: int) -> list[tuple[ItemInstance, ItemPlacement]]:
        result = await self.session.execute(
            select(ItemInstance, ItemPlacement)
            .join(ItemPlacement, ItemPlacement.item_id == ItemInstance.id)
            .where(
                ItemPlacement.holder_type == "character",
                ItemPlacement.holder_id == str(character_id),
                ItemPlacement.storage_type.in_(("equipped", "belt")),
            )
            .order_by(ItemPlacement.storage_type, ItemPlacement.slot.nulls_last(), ItemInstance.name, ItemInstance.id)
        )
        return list(result.all())

    async def count_carried_items(self, character_id: int) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(ItemPlacement)
            .where(
                ItemPlacement.holder_type == "character",
                ItemPlacement.holder_id == str(character_id),
                ItemPlacement.storage_type == "backpack",
            )
        )
        return int(total or 0)

    async def list_carried_items(
        self,
        character_id: int,
        *,
        limit: int,
        offset: int,
    ) -> list[tuple[ItemInstance, ItemPlacement]]:
        result = await self.session.execute(
            select(ItemInstance, ItemPlacement)
            .join(ItemPlacement, ItemPlacement.item_id == ItemInstance.id)
            .where(
                ItemPlacement.holder_type == "character",
                ItemPlacement.holder_id == str(character_id),
                ItemPlacement.storage_type == "backpack",
            )
            .order_by(ItemPlacement.position_index.nulls_last(), ItemInstance.name, ItemInstance.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.all())
