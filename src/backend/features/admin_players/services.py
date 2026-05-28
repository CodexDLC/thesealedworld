from __future__ import annotations

from typing import Any
from uuid import UUID

from src.backend.features.admin_players.dto import (
    AdminPlayerCharacterDetailDTO,
    AdminPlayerCharacterListResponseDTO,
    AdminPlayerCharacterSummaryDTO,
    AdminPlayerEquipmentSlotDTO,
    AdminPlayerInventoryItemDTO,
)
from src.shared.enums.item_enums import EquippedSlot, QuickSlot

_ATTRIBUTE_KEYS = (
    "strength",
    "agility",
    "endurance",
    "intellect",
    "memory",
    "mental",
    "perception",
    "projection",
    "prediction",
)

_EQUIPMENT_LABELS = {
    EquippedSlot.HEAD_ARMOR.value: "Голова",
    EquippedSlot.CHEST_ARMOR.value: "Корпус",
    EquippedSlot.ARMS_ARMOR.value: "Руки",
    EquippedSlot.LEGS_ARMOR.value: "Ноги",
    EquippedSlot.CHEST_GARMENT.value: "Одежда корпуса",
    EquippedSlot.LEGS_GARMENT.value: "Одежда ног",
    EquippedSlot.OUTER_GARMENT.value: "Верхняя одежда",
    EquippedSlot.GLOVES_GARMENT.value: "Перчатки",
    EquippedSlot.FEETWEAR.value: "Обувь",
    EquippedSlot.MAIN_HAND.value: "Основная рука",
    EquippedSlot.OFF_HAND.value: "Вторая рука",
    EquippedSlot.TWO_HAND.value: "Две руки",
    EquippedSlot.AMULET.value: "Амулет",
    EquippedSlot.EARRING.value: "Серьга",
    EquippedSlot.RING_1.value: "Кольцо 1",
    EquippedSlot.RING_2.value: "Кольцо 2",
    EquippedSlot.BELT_ACCESSORY.value: "Пояс",
}


class AdminPlayerReadService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    async def list_characters_for_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> AdminPlayerCharacterListResponseDTO:
        total = await self.repository.count_characters_for_user(user_id)
        characters = await self.repository.list_characters_for_user(user_id, limit=limit, offset=offset)
        return AdminPlayerCharacterListResponseDTO(
            user_id=user_id,
            total=total,
            limit=limit,
            offset=offset,
            items=[_character_summary(character) for character in characters],
        )

    async def get_character_detail(
        self,
        character_id: int,
        *,
        inventory_limit: int,
        inventory_offset: int,
    ) -> AdminPlayerCharacterDetailDTO | None:
        character = await self.repository.get_character_detail(character_id)
        if character is None:
            return None

        active_rows = await self.repository.list_active_items(character_id)
        active_items = [_inventory_item(instance, placement) for instance, placement in active_rows]
        equipped_by_slot = {item.slot: item for item in active_items if item.placement == "equipped" and item.slot}
        belt_by_slot = {item.slot: item for item in active_items if item.placement == "belt" and item.slot}

        carried_total = await self.repository.count_carried_items(character_id)
        carried_rows = await self.repository.list_carried_items(
            character_id,
            limit=inventory_limit,
            offset=inventory_offset,
        )
        return AdminPlayerCharacterDetailDTO(
            character=_character_summary(character),
            attributes=_attributes(character),
            skills=_skills(character),
            free_xp=float(getattr(getattr(character, "progression", None), "free_xp", 0.0) or 0.0),
            equipment_slots=[
                AdminPlayerEquipmentSlotDTO(
                    slot_id=slot.value,
                    label=_EQUIPMENT_LABELS.get(slot.value, slot.value),
                    item=equipped_by_slot.get(slot.value),
                )
                for slot in EquippedSlot
            ],
            belt_slots=[
                AdminPlayerEquipmentSlotDTO(
                    slot_id=slot.value,
                    label=f"Быстрый слот {index}",
                    item=belt_by_slot.get(slot.value),
                )
                for index, slot in enumerate(QuickSlot, start=1)
            ],
            carried_items=[_inventory_item(instance, placement) for instance, placement in carried_rows],
            carried_total=carried_total,
            inventory_limit=inventory_limit,
            inventory_offset=inventory_offset,
        )


def _character_summary(character: Any) -> AdminPlayerCharacterSummaryDTO:
    return AdminPlayerCharacterSummaryDTO(
        character_id=int(character.character_id),
        user_id=character.user_id,
        name=str(character.name),
        name_key=str(character.name_key),
        gender=str(character.gender),
        avatar_url=character.avatar_url,
        game_stage=str(character.game_stage),
        prev_game_stage=character.prev_game_stage,
        location_id=str(character.location_id),
        created_at=character.created_at,
        updated_at=character.updated_at,
    )


def _attributes(character: Any) -> dict[str, int]:
    source = getattr(character, "attributes", None)
    if source is None:
        return {}
    return {key: int(getattr(source, key, 0) or 0) for key in _ATTRIBUTE_KEYS}


def _skills(character: Any) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in getattr(character, "skill_progress", None) or []:
        if not getattr(row, "is_unlocked", False):
            continue
        result[str(row.skill_key)] = float(getattr(row, "total_xp", 0.0) or 0.0)
    return result


def _inventory_item(instance: Any, placement: Any) -> AdminPlayerInventoryItemDTO:
    mechanics = dict(instance.mechanics or {})
    metadata = {**dict(instance.metadata_ or {}), **dict(getattr(instance, "appearance", {}) or {})}
    slot = placement.slot or mechanics.get("slot")
    valid_slots = mechanics.get("valid_slots")
    if not isinstance(valid_slots, list):
        valid_slots = [slot] if slot else []
    return AdminPlayerInventoryItemDTO(
        item_id=str(instance.id),
        base_id=str(instance.base_id),
        name=str(instance.name),
        description=str(instance.description or ""),
        item_type=str(instance.item_type),
        rarity=str(instance.rarity),
        rarity_tier=int(instance.rarity_tier or 0),
        lifecycle_status=str(instance.lifecycle_status),
        text_status=str(instance.text_status),
        placement=str(placement.storage_type),
        slot=str(slot) if slot else None,
        position_index=placement.position_index,
        valid_slots=[str(value) for value in valid_slots if value],
        mechanics={str(key): value for key, value in mechanics.items()},
        metadata={str(key): value for key, value in metadata.items()},
        tags=[str(value) for value in (instance.generation or {}).get("narrative_tags") or []],
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )
