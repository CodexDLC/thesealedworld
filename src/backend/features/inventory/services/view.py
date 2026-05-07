from __future__ import annotations

from src.shared.enums.item_enums import EquippedSlot, QuickSlot
from src.shared.schemas.inventory import (
    InventoryAccessoryRowDTO,
    InventoryBodyZoneDTO,
    InventoryComparisonLineDTO,
    InventoryContainerRowDTO,
    InventoryDetailLineDTO,
    InventoryEffectTagDTO,
    InventoryItemActionDTO,
    InventoryItemDetailsDTO,
    InventoryMetaFieldDTO,
    InventoryQuickSlotDTO,
    InventoryRequirementDTO,
    InventoryRuntimeItemDTO,
    InventoryRuntimeSessionDTO,
    InventoryTabDTO,
    InventoryWindowDTO,
    InventoryWindowSlotDTO,
)

from .projection import belt_capacity, inventory_cell_capacity


class InventoryViewService:
    def build_window(
        self,
        session: InventoryRuntimeSessionDTO,
        *,
        can_act: bool,
        forbidden_reason: str | None = None,
        avatar_url: str | None = None,
        avatar_name: str = "NO_DATA",
        strength: int = 0,
    ) -> InventoryWindowDTO:
        stats = session.stats.model_copy()
        stats.slots_total = inventory_cell_capacity(session, strength=strength)
        stats.slots_used = self._slots_used(session)
        return InventoryWindowDTO(
            char_id=session.char_id,
            can_act=can_act,
            forbidden_reason=forbidden_reason,
            avatar_url=avatar_url,
            avatar_name=avatar_name,
            stats=stats,
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
                InventoryTabDTO(tab_id="items", label="Items", icon="I", is_active=True),
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
            details=self._item_details(session, item) if item else None,
            accepted_slots=[slot_id],
        )

    def _quick_slots(self, session: InventoryRuntimeSessionDTO) -> list[InventoryQuickSlotDTO]:
        capacity = belt_capacity(session)
        result: list[InventoryQuickSlotDTO] = []
        for index, slot in enumerate(QuickSlot, start=1):
            item_id = session.layout.belt.get(slot.value)
            item = session.by_id.get(item_id) if item_id else None
            result.append(
                InventoryQuickSlotDTO(
                    slot_id=slot.value,
                    slot_index=index,
                    item=item,
                    details=self._item_details(session, item) if item else None,
                    enabled=index <= capacity,
                    reason="available" if index <= capacity else "belt_capacity",
                )
            )
        return result

    def _rows(self, session: InventoryRuntimeSessionDTO) -> list[InventoryContainerRowDTO]:
        rows: list[InventoryContainerRowDTO] = []
        for item in session.by_id.values():
            grid_w, grid_h = self._grid_dimensions(item)
            details = self._item_details(session, item)
            rows.append(
                InventoryContainerRowDTO(
                    item_id=item.item_id,
                    icon=str(item.metadata.get("icon_key") or item.item_type[:1].upper()),
                    name=item.name,
                    item_type=item.item_type,
                    weight=self._weight_label(item),
                    quantity=item.quantity,
                    rarity=item.rarity,
                    rarity_tier=details.rarity_tier,
                    rarity_label=details.rarity_label,
                    equip_target=(item.valid_slots[0] if item.valid_slots else item.slot),
                    valid_slots=item.valid_slots,
                    grid_w=grid_w,
                    grid_h=grid_h,
                    is_equipped=item.placement == "equipped",
                    comparison=[
                        InventoryComparisonLineDTO(
                            label=line.label,
                            value=line.value,
                            delta=line.delta,
                            tone=line.tone,
                        )
                        for line in details.comparison
                    ],
                    details=details,
                )
            )
        return rows

    def _item_details(
        self,
        session: InventoryRuntimeSessionDTO,
        item: InventoryRuntimeItemDTO,
    ) -> InventoryItemDetailsDTO:
        comparison_item = self._comparison_item(session, item)
        requirements = self._requirements(item)
        return InventoryItemDetailsDTO(
            item_id=item.item_id,
            name=item.name,
            item_type=item.item_type,
            rarity=item.rarity,
            rarity_tier=self._rarity_tier(item),
            rarity_label=self._rarity_label(item),
            description=item.description,
            flavor=self._flavor(item),
            details=self._detail_lines(item),
            comparison=self._comparison_lines(item, comparison_item) if comparison_item else [],
            effects=self._effect_tags(item),
            tags=[InventoryEffectTagDTO(label=tag) for tag in item.tags],
            requirements=requirements,
            meta=self._meta_fields(item),
            actions=self._actions(session, item, requirements),
        )

    def _comparison_item(
        self,
        session: InventoryRuntimeSessionDTO,
        item: InventoryRuntimeItemDTO,
    ) -> InventoryRuntimeItemDTO | None:
        if item.placement == "equipped":
            return None
        for slot_id in item.valid_slots or ([item.slot] if item.slot else []):
            equipped_id = session.layout.equipment.get(slot_id)
            if equipped_id and equipped_id != item.item_id:
                return session.by_id.get(equipped_id)
        return None

    def _detail_lines(self, item: InventoryRuntimeItemDTO) -> list[InventoryDetailLineDTO]:
        lines: list[InventoryDetailLineDTO] = []
        for key in ("power", "armor", "defense", "damage", "durability_current", "durability_max"):
            if key in item.mechanics and item.mechanics[key] is not None:
                lines.append(
                    self._line(self._label(key), item.mechanics[key], self._tone_for_value(key, item.mechanics[key]))
                )

        bonuses = item.mechanics.get("implicit_bonuses") or {}
        explicit = item.mechanics.get("bonuses") or {}
        if isinstance(bonuses, dict):
            lines.extend(self._bonus_lines(bonuses))
        if isinstance(explicit, dict):
            lines.extend(self._bonus_lines(explicit))

        weight = self._weight_label(item)
        if weight != "-":
            lines.append(InventoryDetailLineDTO(label="Weight", value=weight, tone="neutral"))
        if item.quantity > 1:
            lines.append(InventoryDetailLineDTO(label="Quantity", value=str(item.quantity), tone="neutral"))
        return lines

    def _comparison_lines(
        self,
        item: InventoryRuntimeItemDTO,
        compared: InventoryRuntimeItemDTO,
    ) -> list[InventoryDetailLineDTO]:
        result: list[InventoryDetailLineDTO] = []
        current = self._numeric_stats(item)
        equipped = self._numeric_stats(compared)
        for key, value in current.items():
            if key not in equipped:
                continue
            delta = value - equipped[key]
            if delta == 0:
                continue
            result.append(
                InventoryDetailLineDTO(
                    label=self._label(key),
                    value=self._signed(delta),
                    delta=delta,
                    tone="positive" if delta > 0 else "negative",
                )
            )
        return result

    def _requirements(self, item: InventoryRuntimeItemDTO) -> list[InventoryRequirementDTO]:
        raw = item.mechanics.get("requirements") or item.metadata.get("requirements") or {}
        if isinstance(raw, list):
            return [
                InventoryRequirementDTO(
                    label=str(entry.get("label") or entry.get("key") or "Requirement"),
                    value=str(entry.get("value") or entry.get("required") or ""),
                    met=bool(entry.get("met")),
                    current=str(entry["current"]) if entry.get("current") is not None else None,
                )
                for entry in raw
                if isinstance(entry, dict)
            ]
        if not isinstance(raw, dict):
            return []
        return [
            InventoryRequirementDTO(label=self._label(key), value=str(value), met=bool(value is None or value == 0))
            for key, value in raw.items()
        ]

    def _actions(
        self,
        session: InventoryRuntimeSessionDTO,
        item: InventoryRuntimeItemDTO,
        requirements: list[InventoryRequirementDTO],
    ) -> list[InventoryItemActionDTO]:
        requirements_met = all(requirement.met for requirement in requirements)
        actions: list[InventoryItemActionDTO] = []
        equip_target = item.valid_slots[0] if item.valid_slots else item.slot
        if item.placement == "equipped":
            actions.append(InventoryItemActionDTO(action="unequip", label="Unequip", slot_id=item.slot))
        elif item.placement == "belt":
            actions.append(
                InventoryItemActionDTO(action="remove_from_belt", label="Remove from belt", slot_id=item.slot)
            )
        elif equip_target:
            actions.append(
                InventoryItemActionDTO(
                    action="equip",
                    label="Equip",
                    enabled=requirements_met,
                    reason=None if requirements_met else "requirements",
                    slot_id=equip_target,
                    style="primary",
                )
            )
        if self._is_quick_slot_compatible(item):
            capacity = belt_capacity(session)
            first_free = self._first_free_belt_slot(session, capacity)
            actions.append(
                InventoryItemActionDTO(
                    action="move_to_belt",
                    label="Move to belt",
                    enabled=first_free is not None,
                    reason=None if first_free is not None else "belt_capacity",
                    slot_id=first_free,
                )
            )
        return actions

    def _effect_tags(self, item: InventoryRuntimeItemDTO) -> list[InventoryEffectTagDTO]:
        raw_effects = (
            item.mechanics.get("effects") or item.mechanics.get("triggers") or item.metadata.get("effects") or []
        )
        if isinstance(raw_effects, str):
            raw_effects = [raw_effects]
        if not isinstance(raw_effects, list):
            return []
        return [
            InventoryEffectTagDTO(label=self._label(str(effect)), tone="positive") for effect in raw_effects if effect
        ]

    def _meta_fields(self, item: InventoryRuntimeItemDTO) -> list[InventoryMetaFieldDTO]:
        fields = [
            InventoryMetaFieldDTO(label="Base", value=item.base_id),
            InventoryMetaFieldDTO(label="Type", value=self._label(item.item_type)),
        ]
        if item.slot:
            fields.append(InventoryMetaFieldDTO(label="Slot", value=self._label(item.slot)))
        if item.metadata.get("source"):
            fields.append(InventoryMetaFieldDTO(label="Source", value=str(item.metadata["source"])))
        return fields

    def _numeric_stats(self, item: InventoryRuntimeItemDTO) -> dict[str, float]:
        stats: dict[str, float] = {}
        for key in ("power", "armor", "defense", "damage"):
            value = self._float_value(item.mechanics.get(key))
            if value is not None:
                stats[key] = value
        for source in (item.mechanics.get("implicit_bonuses"), item.mechanics.get("bonuses")):
            if not isinstance(source, dict):
                continue
            for key, raw in source.items():
                value = self._float_value(raw)
                if value is not None:
                    stats[str(key)] = stats.get(str(key), 0.0) + value
        return stats

    def _bonus_lines(self, bonuses: dict[str, object]) -> list[InventoryDetailLineDTO]:
        lines: list[InventoryDetailLineDTO] = []
        for key, raw in bonuses.items():
            value = self._float_value(raw)
            if value is None:
                lines.append(InventoryDetailLineDTO(label=self._label(str(key)), value=str(raw), tone="neutral"))
                continue
            lines.append(
                InventoryDetailLineDTO(
                    label=self._label(str(key)),
                    value=self._signed(value),
                    tone="positive" if value > 0 else "negative" if value < 0 else "neutral",
                )
            )
        return lines

    def _slots_used(self, session: InventoryRuntimeSessionDTO) -> int:
        total = 0
        for item_id in session.layout.backpack:
            item = session.by_id.get(item_id)
            if item is None:
                continue
            grid_w, grid_h = self._grid_dimensions(item)
            total += grid_w * grid_h
        return total

    @staticmethod
    def _item_in_equipment_slot(session: InventoryRuntimeSessionDTO, slot_id: str) -> InventoryRuntimeItemDTO | None:
        item_id = session.layout.equipment.get(slot_id)
        return session.by_id.get(item_id) if item_id else None

    @staticmethod
    def _grid_dimensions(item: InventoryRuntimeItemDTO) -> tuple[int, int]:
        fallback_by_type = {
            "weapon": (4, 2),
            "armor": (4, 2),
            "garment": (3, 2),
            "footwear": (3, 2),
            "accessory": (2, 2),
            "consumable": (2, 1),
            "resource": (2, 1),
            "currency": (2, 1),
            "material": (2, 1),
            "quest": (2, 1),
        }
        fallback_w, fallback_h = fallback_by_type.get(item.item_type, (2, 2))
        width = InventoryViewService._positive_int(item.metadata.get("width_cells"))
        height = InventoryViewService._positive_int(item.metadata.get("height_cells"))

        if width <= 1 and height <= 1:
            width, height = fallback_w, fallback_h

        return max(1, min(8, width)), max(1, min(4, height))

    @staticmethod
    def _weight_label(item: InventoryRuntimeItemDTO) -> str:
        raw = (
            item.metadata.get("weight")
            or item.metadata.get("weight_units")
            or item.metadata.get("volume_units")
            or item.mechanics.get("weight")
            or item.mechanics.get("weight_units")
        )
        if raw is None:
            return "-"
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return str(raw)
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _rarity_tier(item: InventoryRuntimeItemDTO) -> int:
        try:
            return max(0, min(7, int(item.rarity_tier)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _rarity_label(item: InventoryRuntimeItemDTO) -> str:
        labels = ["Common", "Uncommon", "Advanced", "Rare", "Epic", "Mythic", "Legendary", "Absolute"]
        return labels[InventoryViewService._rarity_tier(item)]

    @staticmethod
    def _flavor(item: InventoryRuntimeItemDTO) -> str | None:
        for key in ("flavor", "flavor_text", "lore", "lore_text"):
            raw = item.metadata.get(key)
            if raw:
                return str(raw)
        return None

    @staticmethod
    def _line(label: str, raw: object, tone: str) -> InventoryDetailLineDTO:
        value = InventoryViewService._float_value(raw)
        return InventoryDetailLineDTO(
            label=label,
            value=InventoryViewService._signed(value) if value is not None else str(raw),
            tone=tone,  # type: ignore[arg-type]
        )

    @staticmethod
    def _tone_for_value(key: str, raw: object) -> str:
        value = InventoryViewService._float_value(raw)
        if value is None or value == 0 or key.startswith("durability"):
            return "neutral"
        return "positive" if value > 0 else "negative"

    @staticmethod
    def _float_value(raw: object) -> float | None:
        try:
            return float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _signed(value: float) -> str:
        number = str(int(abs(value))) if value.is_integer() else f"{abs(value):.2f}".rstrip("0").rstrip(".")
        return f"+{number}" if value > 0 else f"-{number}" if value < 0 else "0"

    @staticmethod
    def _label(key: str) -> str:
        return key.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _is_quick_slot_compatible(item: InventoryRuntimeItemDTO) -> bool:
        return bool(item.mechanics.get("is_quick_slot_compatible") or item.mechanics.get("quick_slot_compatible"))

    @staticmethod
    def _first_free_belt_slot(session: InventoryRuntimeSessionDTO, capacity: int) -> str | None:
        for index, slot in enumerate(QuickSlot, start=1):
            if index > capacity:
                return None
            if not session.layout.belt.get(slot.value):
                return slot.value
        return None

    @staticmethod
    def _positive_int(raw: object) -> int:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0
