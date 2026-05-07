from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from src.backend.features.inventory.repositories.items import runtime_item_from_instance
from src.backend.features.inventory.services.projection import (
    BACKPACK_STORAGE,
    BELT_STORAGE,
    EQUIPMENT_STORAGE,
    belt_capacity,
    build_active_character_projection,
    build_runtime_session,
    compatible_with_slot,
    is_quick_slot_compatible,
)
from src.backend.features.inventory.services.view import InventoryViewService
from src.shared.enums import CoreDomain
from src.shared.enums.item_enums import EquippedSlot, QuickSlot
from src.shared.schemas.inventory import (
    InventoryActionForbiddenDTO,
    InventoryActionRequestDTO,
    InventoryRuntimeItemDTO,
    InventoryRuntimeSessionDTO,
    InventoryWindowDTO,
)

if TYPE_CHECKING:
    from src.backend.features.character.managers.session import CharacterSessionManager
    from src.backend.features.inventory.repositories.items import InventoryItemRepository
    from src.backend.features.inventory.services.session_manager import InventorySessionManager


class InventoryActionForbiddenError(RuntimeError):
    def __init__(self, payload: InventoryActionForbiddenDTO) -> None:
        super().__init__(payload.message)
        self.payload = payload


class InventoryActionError(ValueError):
    """Raised for invalid inventory actions in an otherwise allowed state."""


class InventoryService:
    FORBIDDEN_ACTION_STATES = {CoreDomain.SCENARIO.value, CoreDomain.COMBAT.value, "combat"}

    def __init__(
        self,
        *,
        repository: InventoryItemRepository,
        inventory_sessions: InventorySessionManager,
        character_sessions: CharacterSessionManager,
        view_service: InventoryViewService | None = None,
    ) -> None:
        self.repository = repository
        self.inventory_sessions = inventory_sessions
        self.character_sessions = character_sessions
        self.view_service = view_service or InventoryViewService()

    async def open_window(self, char_id: int) -> InventoryWindowDTO:
        session = await self.get_or_create_session(char_id)
        state = await self._current_state(char_id)
        can_act = self._can_act(state)
        return self.view_service.build_window(
            session,
            can_act=can_act,
            forbidden_reason=None if can_act else InventoryActionForbiddenDTO(state=state).message,
            **await self._avatar_context(char_id),
            **await self._attribute_context(char_id),
        )

    async def apply_action(self, dto: InventoryActionRequestDTO) -> InventoryWindowDTO:
        await self._ensure_can_act(dto.char_id)
        session = await self.get_or_create_session(dto.char_id)

        if dto.action == "equip":
            self._equip(session, dto.item_id, self._require_slot(dto))
        elif dto.action == "unequip":
            self._unequip(session, dto.item_id)
        elif dto.action == "move_to_belt":
            self._move_to_belt(session, dto.item_id, self._require_slot(dto))
        elif dto.action == "remove_from_belt":
            self._remove_from_belt(session, dto.item_id)
        else:
            raise InventoryActionError(f"Inventory action is not implemented yet: {dto.action}")

        session.is_dirty = True
        session.updated_at = time.time()
        await self.inventory_sessions.set(session)
        await self._sync_active_character_items(session)
        return self.view_service.build_window(
            session,
            can_act=True,
            **await self._avatar_context(dto.char_id),
            **await self._attribute_context(dto.char_id),
        )

    async def close_window(self, char_id: int) -> InventoryWindowDTO:
        session = await self.get_or_create_session(char_id)
        if session.is_dirty:
            await self.flush_session(session)
        await self.inventory_sessions.delete(char_id)
        await self.character_sessions.clear_inventory_session(char_id)
        return self.view_service.build_window(
            session,
            can_act=True,
            **await self._avatar_context(char_id),
            **await self._attribute_context(char_id),
        )

    async def get_or_create_session(self, char_id: int) -> InventoryRuntimeSessionDTO:
        session = await self.inventory_sessions.get(char_id)
        if session is not None:
            await self.inventory_sessions.touch(char_id)
            return session

        rows = await self.repository.list_character_items(char_id)
        runtime_items = [runtime_item_from_instance(instance, placement) for instance, placement in rows]
        session = build_runtime_session(char_id, runtime_items)
        session.updated_at = time.time()
        await self.inventory_sessions.set(session)
        await self.character_sessions.set_inventory_session(char_id, self.inventory_sessions.build_key(char_id))
        await self._sync_active_character_items(session)
        return session

    async def flush_session(self, session: InventoryRuntimeSessionDTO) -> None:
        await self.repository.save_placements(session.char_id, session.by_id)
        await self.repository.commit()
        session.is_dirty = False
        session.updated_at = time.time()
        await self.inventory_sessions.set(session)
        await self._sync_active_character_items(session)

    async def _sync_active_character_items(self, session: InventoryRuntimeSessionDTO) -> None:
        projection = build_active_character_projection(session)
        await self.character_sessions.set_items_projection(session.char_id, projection.model_dump(mode="json"))

    def _equip(self, session: InventoryRuntimeSessionDTO, item_id: str, slot_id: str) -> None:
        if slot_id not in {slot.value for slot in EquippedSlot}:
            raise InventoryActionError(f"Unknown equipment slot: {slot_id}")
        item = self._item(session, item_id)
        if not compatible_with_slot(item, slot_id):
            raise InventoryActionError(f"Item {item_id} cannot be equipped into {slot_id}")

        self._clear_equipment_slot(session, slot_id)
        if slot_id == EquippedSlot.TWO_HAND.value:
            self._clear_equipment_slot(session, EquippedSlot.MAIN_HAND.value)
            self._clear_equipment_slot(session, EquippedSlot.OFF_HAND.value)
        elif slot_id in {EquippedSlot.MAIN_HAND.value, EquippedSlot.OFF_HAND.value}:
            self._clear_equipment_slot(session, EquippedSlot.TWO_HAND.value)

        self._detach_item(session, item_id)
        item.placement = EQUIPMENT_STORAGE
        item.slot = slot_id
        session.layout.equipment[slot_id] = item_id
        self._enforce_belt_capacity(session)

    def _unequip(self, session: InventoryRuntimeSessionDTO, item_id: str) -> None:
        item = self._item(session, item_id)
        self._detach_item(session, item_id)
        item.placement = BACKPACK_STORAGE
        item.slot = None
        if item_id not in session.layout.backpack:
            session.layout.backpack.append(item_id)
        self._enforce_belt_capacity(session)

    def _move_to_belt(self, session: InventoryRuntimeSessionDTO, item_id: str, slot_id: str) -> None:
        if slot_id not in {slot.value for slot in QuickSlot}:
            raise InventoryActionError(f"Unknown belt slot: {slot_id}")
        slot_index = list(QuickSlot).index(QuickSlot(slot_id)) + 1
        if slot_index > belt_capacity(session):
            raise InventoryActionError(f"Belt slot is not available: {slot_id}")
        item = self._item(session, item_id)
        if not is_quick_slot_compatible(item):
            raise InventoryActionError(f"Item {item_id} cannot be placed into the belt")

        self._clear_belt_slot(session, slot_id)
        self._detach_item(session, item_id)
        item.placement = BELT_STORAGE
        item.slot = slot_id
        session.layout.belt[slot_id] = item_id

    def _remove_from_belt(self, session: InventoryRuntimeSessionDTO, item_id: str) -> None:
        item = self._item(session, item_id)
        if item.placement != BELT_STORAGE:
            raise InventoryActionError(f"Item {item_id} is not in the belt")
        self._detach_item(session, item_id)
        item.placement = BACKPACK_STORAGE
        item.slot = None
        if item_id not in session.layout.backpack:
            session.layout.backpack.append(item_id)

    def _detach_item(self, session: InventoryRuntimeSessionDTO, item_id: str) -> None:
        for slot, equipped_id in list(session.layout.equipment.items()):
            if equipped_id == item_id:
                session.layout.equipment[slot] = None
        for slot, belt_id in list(session.layout.belt.items()):
            if belt_id == item_id:
                session.layout.belt[slot] = None
        session.layout.backpack = [value for value in session.layout.backpack if value != item_id]

    def _clear_equipment_slot(self, session: InventoryRuntimeSessionDTO, slot_id: str) -> None:
        item_id = session.layout.equipment.get(slot_id)
        if item_id:
            item = session.by_id.get(item_id)
            if item:
                item.placement = BACKPACK_STORAGE
                item.slot = None
                if item_id not in session.layout.backpack:
                    session.layout.backpack.append(item_id)
        session.layout.equipment[slot_id] = None

    def _clear_belt_slot(self, session: InventoryRuntimeSessionDTO, slot_id: str) -> None:
        item_id = session.layout.belt.get(slot_id)
        if item_id:
            item = session.by_id.get(item_id)
            if item:
                item.placement = BACKPACK_STORAGE
                item.slot = None
                if item_id not in session.layout.backpack:
                    session.layout.backpack.append(item_id)
        session.layout.belt[slot_id] = None

    def _enforce_belt_capacity(self, session: InventoryRuntimeSessionDTO) -> None:
        capacity = belt_capacity(session)
        for index, slot in enumerate(QuickSlot, start=1):
            if index > capacity and session.layout.belt.get(slot.value):
                self._clear_belt_slot(session, slot.value)

    def _item(self, session: InventoryRuntimeSessionDTO, item_id: str) -> InventoryRuntimeItemDTO:
        item = session.by_id.get(item_id)
        if item is None:
            raise InventoryActionError(f"Inventory item not found: {item_id}")
        return item

    async def _ensure_can_act(self, char_id: int) -> None:
        state = await self._current_state(char_id)
        if not self._can_act(state):
            raise InventoryActionForbiddenError(InventoryActionForbiddenDTO(state=state))

    async def _current_state(self, char_id: int) -> str | None:
        raw = await self.character_sessions.get_section(char_id, "state")
        return str(raw) if raw is not None else None

    def _can_act(self, state: str | None) -> bool:
        return state not in self.FORBIDDEN_ACTION_STATES

    async def _avatar_context(self, char_id: int) -> dict[str, Any]:
        bio = await self.character_sessions.get_section(char_id, "bio")
        if not isinstance(bio, dict):
            return {"avatar_url": None, "avatar_name": "NO_DATA"}
        return {"avatar_url": bio.get("avatar"), "avatar_name": str(bio.get("name") or "NO_DATA")}

    async def _attribute_context(self, char_id: int) -> dict[str, Any]:
        attributes = await self.character_sessions.get_section(char_id, "attributes")
        if not isinstance(attributes, dict):
            return {"strength": 0}
        try:
            strength = int(attributes.get("strength") or 0)
        except (TypeError, ValueError):
            strength = 0
        return {"strength": max(0, strength)}

    @staticmethod
    def _require_slot(dto: InventoryActionRequestDTO) -> str:
        if not dto.slot_id:
            raise InventoryActionError(f"Inventory action requires slot_id: {dto.action}")
        return dto.slot_id
