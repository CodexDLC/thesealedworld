from __future__ import annotations

from src.shared.enums.item_enums import EquippedSlot, QuickSlot
from src.shared.schemas.inventory import (
    InventoryAccessoryRowDTO,
    InventoryBodyZoneDTO,
    InventoryContainerRowDTO,
    InventoryQuickSlotDTO,
    InventoryRuntimeItemDTO,
    InventoryRuntimeSessionDTO,
    InventoryTabDTO,
    InventoryWindowDTO,
    InventoryWindowSlotDTO,
)

from .projection import belt_capacity


class InventoryViewService:
    def build_window(
        self,
        session: InventoryRuntimeSessionDTO,
        *,
        can_act: bool,
        forbidden_reason: str | None = None,
        avatar_url: str | None = None,
        avatar_name: str = "NO_DATA",
    ) -> InventoryWindowDTO:
        return InventoryWindowDTO(
            char_id=session.char_id,
            can_act=can_act,
            forbidden_reason=forbidden_reason,
            avatar_url=avatar_url,
            avatar_name=avatar_name,
            body_zones=[
                self._zone(session, "head", "Head", EquippedSlot.HEAD_ARMOR.value, "Helmet", "armor", "head"),
                self._zone(session, "outer", "Cloak", EquippedSlot.OUTER_GARMENT.value, "Cloak", "garment", "outer"),
                self._zone(
                    session,
                    "chest",
                    "Torso",
                    EquippedSlot.CHEST_ARMOR.value,
                    "Armor",
                    "armor",
                    "chest",
                    secondary=(EquippedSlot.CHEST_GARMENT.value, "Clothing", "garment"),
                ),
                self._zone(
                    session,
                    "arms",
                    "Arms",
                    EquippedSlot.ARMS_ARMOR.value,
                    "Bracers",
                    "armor",
                    "arms",
                    secondary=(EquippedSlot.GLOVES_GARMENT.value, "Gloves", "garment"),
                ),
                self._zone(
                    session,
                    "legs",
                    "Legs",
                    EquippedSlot.LEGS_ARMOR.value,
                    "Leg Armor",
                    "armor",
                    "legs",
                    secondary=(EquippedSlot.LEGS_GARMENT.value, "Pants", "garment"),
                ),
                self._zone(session, "feet", "Footwear", EquippedSlot.FEETWEAR.value, "Boots", "equipment", "feet"),
            ],
            weapon_slots=[
                self._slot(session, EquippedSlot.MAIN_HAND.value, "Main Hand", "equipment"),
                self._slot(session, EquippedSlot.OFF_HAND.value, "Off Hand", "equipment"),
            ],
            accessory_rows=[
                InventoryAccessoryRowDTO(
                    row_id="amulet",
                    label="Amulet",
                    slots=[self._slot(session, EquippedSlot.AMULET.value, "Amulet", "accessory")],
                ),
                InventoryAccessoryRowDTO(
                    row_id="earrings",
                    label="Earrings",
                    slots=[self._slot(session, EquippedSlot.EARRING.value, "Earrings", "accessory")],
                ),
                InventoryAccessoryRowDTO(
                    row_id="rings",
                    label="Rings",
                    slots=[
                        self._slot(session, EquippedSlot.RING_1.value, "Ring 1", "accessory"),
                        self._slot(session, EquippedSlot.RING_2.value, "Ring 2", "accessory"),
                    ],
                    is_wide=False,
                ),
                InventoryAccessoryRowDTO(
                    row_id="belt",
                    label="Belt",
                    slots=[self._slot(session, EquippedSlot.BELT_ACCESSORY.value, "Belt", "accessory")],
                ),
            ],
            quick_slots=self._quick_slots(session),
            tabs=[
                InventoryTabDTO(tab_id="equipped", label="Equipped", icon="E", is_active=True),
                InventoryTabDTO(tab_id="items", label="Items", icon="I"),
                InventoryTabDTO(tab_id="resources", label="Resources", icon="R"),
                InventoryTabDTO(tab_id="quest", label="Quest", icon="Q"),
            ],
            visible_rows=self._rows(session),
        )

    def _zone(
        self,
        session: InventoryRuntimeSessionDTO,
        zone_id: str,
        label: str,
        slot_id: str,
        slot_label: str,
        layer: str,
        position: str,
        *,
        secondary: tuple[str, str, str] | None = None,
    ) -> InventoryBodyZoneDTO:
        return InventoryBodyZoneDTO(
            zone_id=zone_id,
            label=label,
            primary_slot=self._slot(session, slot_id, slot_label, layer),
            secondary_slot=self._slot(session, *secondary) if secondary else None,
            position=position,
        )

    def _slot(
        self,
        session: InventoryRuntimeSessionDTO,
        slot_id: str,
        label: str,
        layer: str,
    ) -> InventoryWindowSlotDTO:
        item = self._item_in_equipment_slot(session, slot_id)
        return InventoryWindowSlotDTO(
            slot_id=slot_id,
            label=label,
            layer=layer,  # type: ignore[arg-type]
            item=item,
            accepted_slots=[slot_id],
        )

    def _quick_slots(self, session: InventoryRuntimeSessionDTO) -> list[InventoryQuickSlotDTO]:
        capacity = belt_capacity(session)
        result: list[InventoryQuickSlotDTO] = []
        for index, slot in enumerate(QuickSlot, start=1):
            item_id = session.layout.belt.get(slot.value)
            result.append(
                InventoryQuickSlotDTO(
                    slot_id=slot.value,
                    slot_index=index,
                    item=session.by_id.get(item_id) if item_id else None,
                    enabled=index <= capacity,
                    reason="available" if index <= capacity else "belt_capacity",
                )
            )
        return result

    def _rows(self, session: InventoryRuntimeSessionDTO) -> list[InventoryContainerRowDTO]:
        rows: list[InventoryContainerRowDTO] = []
        for item in session.by_id.values():
            rows.append(
                InventoryContainerRowDTO(
                    item_id=item.item_id,
                    icon=str(item.metadata.get("icon_key") or item.item_type[:1].upper()),
                    name=item.name,
                    item_type=item.item_type,
                    quantity=item.quantity,
                    rarity=item.rarity,
                    equip_target=(item.valid_slots[0] if item.valid_slots else item.slot),
                    comparison=[],
                )
            )
        return rows

    @staticmethod
    def _item_in_equipment_slot(session: InventoryRuntimeSessionDTO, slot_id: str) -> InventoryRuntimeItemDTO | None:
        item_id = session.layout.equipment.get(slot_id)
        return session.by_id.get(item_id) if item_id else None
