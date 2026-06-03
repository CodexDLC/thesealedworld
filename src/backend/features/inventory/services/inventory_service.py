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
    InventoryTabId,
    InventoryWindowDTO,
    WalletDTO,
)

if TYPE_CHECKING:
    from src.backend.features.inventory.integrations import InventoryStreamClient
    from src.backend.features.inventory.repositories.items import InventoryItemRepository
    from src.backend.infrastructure.actor_state.managers import CharacterSessionManager
    from src.backend.infrastructure.inventory.managers import InventorySessionManager


class InventoryActionForbiddenError(RuntimeError):
    def __init__(self, payload: InventoryActionForbiddenDTO) -> None:
        super().__init__(payload.message)
        self.payload = payload


class InventoryActionError(ValueError):
    """Raised for invalid inventory actions in an otherwise allowed state."""


class InventoryService:
    FORBIDDEN_ACTION_STATES = {
        CoreDomain.SCENARIO.value,
        CoreDomain.COMBAT.value,
        CoreDomain.COMBAT_RESULT.value,
        CoreDomain.DEATH.value,
        "combat",
    }

    def __init__(
        self,
        *,
        repository: InventoryItemRepository,
        inventory_sessions: InventorySessionManager,
        character_sessions: CharacterSessionManager,
        stream_client: InventoryStreamClient,
        view_service: InventoryViewService | None = None,
    ) -> None:
        self.repository = repository
        self.inventory_sessions = inventory_sessions
        self.character_sessions = character_sessions
        self.stream_client = stream_client
        self.view_service = view_service or InventoryViewService()

    async def open_window(self, char_id: int, *, active_tab: InventoryTabId = "items") -> InventoryWindowDTO:
        session = await self.get_or_create_session(char_id)
        state = await self._current_state(char_id)
        can_act = self._can_act(state)
        return self.view_service.build_window(
            session,
            can_act=can_act,
            active_tab=active_tab,
            forbidden_reason=None if can_act else InventoryActionForbiddenDTO(state=state).message,
            **await self._avatar_context(char_id),
            **await self._attribute_context(char_id),
        )

    async def apply_action(
        self, dto: InventoryActionRequestDTO, *, active_tab: InventoryTabId = "items"
    ) -> InventoryWindowDTO:
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
        elif dto.action == "drop":
            await self._drop(session, dto.item_id)
        else:
            raise InventoryActionError(f"Inventory action is not implemented yet: {dto.action}")

        session.is_dirty = True
        session.dirty = {
            "dirty": True,
            "reason": dto.action,
            "paths": ["$.layout", "$.by_id"],
            "updated_at": time.time(),
        }
        session.updated_at = time.time()
        await self.inventory_sessions.set(session)
        await self._sync_active_character_items(session, reason=dto.action)
        return self.view_service.build_window(
            session,
            can_act=True,
            active_tab=active_tab,
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
        active_run_id = await self._active_run_id(char_id)
        session = await self.inventory_sessions.get(char_id)
        if session is not None:
            if self._session_run_context_changed(session, active_run_id):
                await self.inventory_sessions.delete(char_id)
                session = None
            else:
                session.risk_run_id = active_run_id
                await self.inventory_sessions.touch(char_id)
                await self._refresh_wallet(session)
                return session

        rows = await self.repository.list_character_items(char_id, expedition_run_id=active_run_id)
        runtime_items = [runtime_item_from_instance(instance, placement) for instance, placement in rows]
        session = build_runtime_session(char_id, runtime_items, risk_run_id=active_run_id)
        await self._refresh_wallet(session)
        session.updated_at = time.time()
        await self.inventory_sessions.set(session)
        await self.character_sessions.set_inventory_session(char_id, self.inventory_sessions.build_key(char_id))
        await self._sync_active_character_items(session, reason="inventory_opened")
        return session

    async def _refresh_wallet(self, session: InventoryRuntimeSessionDTO) -> None:
        get_wallet = getattr(self.repository, "get_wallet", None)
        wallet = await get_wallet(session.char_id) if get_wallet is not None else WalletDTO()

        run_id = await self._active_run_id(session.char_id)
        get_expedition_wallet = getattr(self.repository, "get_expedition_wallet", None)
        if run_id and get_expedition_wallet is not None:
            wallet = self._merge_wallets(wallet, await get_expedition_wallet(run_id))

        session.wallet = wallet

    async def flush_session(self, session: InventoryRuntimeSessionDTO) -> None:
        await self.repository.save_placements(
            session.char_id,
            session.by_id,
            expedition_run_id=await self._active_run_id(session.char_id),
        )
        await self.repository.commit()
        session.is_dirty = False
        session.dirty = {"dirty": False, "last_flushed_at": time.time()}
        session.updated_at = time.time()
        await self.inventory_sessions.set(session)
        await self._sync_active_character_items(session, reason="inventory_flushed")

    async def apply_durability_damage(
        self,
        *,
        char_id: int,
        amount: float,
        scope: str = "equipped",
        reason: str = "combat_completed",
        source: str = "combat_finalization",
        combat_id: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del source, combat_id, metadata
        damage = max(0.0, float(amount or 0.0))
        if damage <= 0:
            return {"status": "skipped", "changed": [], "reason": "zero_damage"}
        if idempotency_key and await self._durability_event_processed(char_id, idempotency_key):
            return {"status": "skipped", "changed": [], "reason": "duplicate_event"}

        session = await self.get_or_create_session(char_id)
        changed: list[dict[str, Any]] = []
        for item in self._durability_scope_items(session, scope):
            before = self._durability_current(item)
            maximum = self._durability_max(item)
            if before is None and maximum is None:
                continue
            current = before if before is not None else maximum
            if current is None:
                continue
            after = max(0.0, round(current - damage, 4))
            if after == before:
                continue
            item.mechanics["durability_current"] = after
            if maximum is not None:
                item.mechanics["durability_max"] = maximum
            changed.append({"item_id": item.item_id, "before": current, "after": after})

        if not changed:
            return {"status": "skipped", "changed": [], "reason": "no_durable_items"}

        session.is_dirty = True
        session.dirty = {
            "dirty": True,
            "reason": reason,
            "paths": ["$.by_id"],
            "updated_at": time.time(),
            "idempotency_key": idempotency_key,
        }
        session.updated_at = time.time()
        await self.inventory_sessions.set(session)
        await self.repository.save_item_mechanics(session.by_id)
        await self.repository.commit()
        await self._sync_active_character_items(session, reason=reason)
        if idempotency_key:
            await self._mark_durability_event_processed(char_id, idempotency_key, changed=changed, reason=reason)
        return {"status": "ok", "changed": changed, "reason": reason}

    async def _sync_active_character_items(self, session: InventoryRuntimeSessionDTO, *, reason: str) -> None:
        projection = build_active_character_projection(session)
        await self.character_sessions.set_items_projection(session.char_id, projection.model_dump(mode="json"))
        await self.stream_client.request_gear_score_recalculation(char_id=session.char_id, reason=reason)
        if reason in {"equip", "unequip", "reward_granted"}:
            vitals_refresh = await self.character_sessions.refresh_vitals_max(session.char_id)
            if vitals_refresh.get("changed") is True:
                await self.stream_client.request_status_refresh(char_id=session.char_id, reason=reason)

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

    async def _drop(self, session: InventoryRuntimeSessionDTO, item_id: str) -> None:
        self._item(session, item_id)
        discarded = await self.repository.discard_character_item(
            session.char_id,
            item_id,
            expedition_run_id=await self._active_run_id(session.char_id),
            reason="inventory_drop",
        )
        if not discarded:
            raise InventoryActionError(f"Inventory item cannot be dropped: {item_id}")
        await self.repository.commit()
        self._detach_item(session, item_id)
        session.by_id.pop(item_id, None)

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

    def _durability_scope_items(
        self,
        session: InventoryRuntimeSessionDTO,
        scope: str,
    ) -> list[InventoryRuntimeItemDTO]:
        item_ids: list[str] = []
        if scope in {"equipped", "all_active", "all_carried"}:
            item_ids.extend(str(item_id) for item_id in session.layout.equipment.values() if item_id)
        if scope in {"belt", "all_active", "all_carried"}:
            item_ids.extend(str(item_id) for item_id in session.layout.belt.values() if item_id)
        if scope == "all_carried":
            item_ids.extend(str(item_id) for item_id in session.layout.backpack if item_id)
        seen: set[str] = set()
        result: list[InventoryRuntimeItemDTO] = []
        for item_id in item_ids:
            if item_id in seen:
                continue
            seen.add(item_id)
            item = session.by_id.get(item_id)
            if item is not None:
                result.append(item)
        return result

    @staticmethod
    def _durability_current(item: InventoryRuntimeItemDTO) -> float | None:
        return InventoryService._optional_float(item.mechanics.get("durability_current"))

    @staticmethod
    def _durability_max(item: InventoryRuntimeItemDTO) -> float | None:
        return InventoryService._optional_float(item.mechanics.get("durability_max"))

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def _durability_event_processed(self, char_id: int, idempotency_key: str) -> bool:
        processed = await self.character_sessions.get_section(char_id, "processed_events")
        return isinstance(processed, dict) and idempotency_key in processed

    async def _mark_durability_event_processed(
        self,
        char_id: int,
        idempotency_key: str,
        *,
        changed: list[dict[str, Any]],
        reason: str,
    ) -> None:
        processed = await self.character_sessions.get_section(char_id, "processed_events")
        payload = dict(processed) if isinstance(processed, dict) else {}
        payload[idempotency_key] = {
            "type": "inventory_durability_damage",
            "reason": reason,
            "changed_count": len(changed),
            "processed_at": time.time(),
        }
        await self.character_sessions.patch_fields(char_id, {"$.processed_events": payload})
        await self.character_sessions.mark_dirty(
            char_id,
            reason="inventory_durability_damage_processed",
            paths=["$.processed_events", "$.items"],
        )

    async def _ensure_can_act(self, char_id: int) -> None:
        state = await self._current_state(char_id)
        if not self._can_act(state):
            raise InventoryActionForbiddenError(InventoryActionForbiddenDTO(state=state))

    async def _current_state(self, char_id: int) -> str | None:
        raw = await self.character_sessions.get_section(char_id, "state")
        return str(raw) if raw is not None else None

    async def _active_run_id(self, char_id: int) -> str | None:
        risk = await self.character_sessions.get_section(char_id, "risk")
        if not isinstance(risk, dict):
            return None
        run_id = risk.get("run_id")
        return str(run_id) if run_id else None

    @staticmethod
    def _session_run_context_changed(session: InventoryRuntimeSessionDTO, active_run_id: str | None) -> bool:
        if session.risk_run_id != active_run_id:
            return True
        if active_run_id is None:
            return any(item.is_unsecured or item.sync_state == "unsecured" for item in session.by_id.values())
        return False

    @staticmethod
    def _merge_wallets(base: WalletDTO, extra: WalletDTO) -> WalletDTO:
        return WalletDTO(
            currency=InventoryService._merge_bucket(base.currency, extra.currency),
            resources=InventoryService._merge_bucket(base.resources, extra.resources),
            components=InventoryService._merge_bucket(base.components, extra.components),
        )

    @staticmethod
    def _merge_bucket(base: dict[str, int], extra: dict[str, int]) -> dict[str, int]:
        merged = {str(key): int(value or 0) for key, value in base.items()}
        for key, value in extra.items():
            amount = int(value or 0)
            if amount <= 0:
                continue
            merged[str(key)] = merged.get(str(key), 0) + amount
        return {key: value for key, value in merged.items() if value > 0}

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
