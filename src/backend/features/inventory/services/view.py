from __future__ import annotations

from typing import Any

from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG
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
    _NON_PERCENT_STAT_KEYS = {
        "power",
        "armor",
        "defense",
        "damage",
        "durability_current",
        "durability_max",
        "weight",
        "weight_units",
        "hp_max",
        "energy_max",
        "hp_regen",
        "energy_regen",
        "stamina_regen",
        "en_regen",
        "inventory_cell_capacity",
        "inventory_slot_capacity",
        "inventory_slots",
        "quick_slot_capacity",
        "environment_cold_resistance",
        "environment_heat_resistance",
        "perception",
        "initiative",
        "intelligence",
        "memory",
        "stamina",
        "strength",
    }
    _PERCENT_STAT_KEYS = {
        "accuracy_penalty",
        "anti_crit_chance",
        "anti_dodge_chance",
        "armor_penetration",
        "bleed_damage_bonus",
        "bleed_resistance",
        "counter_attack_chance",
        "crafting_speed",
        "debuff_avoidance",
        "dodge_chance",
        "evasion",
        "evasion_penalty",
        "find_loot_chance",
        "fire_damage_bonus",
        "fire_resistance",
        "main_hand_accuracy",
        "magical_damage_bonus",
        "magical_penetration",
        "magical_resistance",
        "magic_resist",
        "parry_chance",
        "physical_accuracy",
        "physical_crit_chance",
        "physical_crit_power_float",
        "physical_damage_bonus",
        "physical_penetration",
        "physical_resistance",
        "phys_accuracy",
        "phys_resist",
        "shield_block_chance",
        "shock_resistance",
        "thorns_damage_reflect",
        "vampiric_power",
        "water_resistance",
    }

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
            if item.placement != "backpack":
                continue
            grid_w, grid_h = self._grid_dimensions(item)
            details = self._item_details(session, item)
            rows.append(
                InventoryContainerRowDTO(
                    item_id=item.item_id,
                    icon=self._icon_key(item),
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

    def _icon_key(self, item: InventoryRuntimeItemDTO) -> str:
        slot = item.slot or (item.valid_slots[0] if item.valid_slots else "")
        slot_icons = {
            EquippedSlot.HEAD_ARMOR.value: "head",
            EquippedSlot.OUTER_GARMENT.value: "cloak",
            EquippedSlot.CHEST_ARMOR.value: "torso",
            EquippedSlot.CHEST_GARMENT.value: "garment",
            EquippedSlot.ARMS_ARMOR.value: "arms",
            EquippedSlot.GLOVES_GARMENT.value: "arms",
            EquippedSlot.LEGS_ARMOR.value: "legs",
            EquippedSlot.LEGS_GARMENT.value: "legs",
            EquippedSlot.FEETWEAR.value: "feetwear",
            EquippedSlot.MAIN_HAND.value: "weapon",
            EquippedSlot.TWO_HAND.value: "weapon",
            EquippedSlot.AMULET.value: "amulet",
            EquippedSlot.EARRING.value: "earrings",
            EquippedSlot.RING_1.value: "ring",
            EquippedSlot.RING_2.value: "ring",
            EquippedSlot.BELT_ACCESSORY.value: "belt",
        }
        if slot == EquippedSlot.OFF_HAND.value:
            if item.item_type == "armor" or "shield" in item.tags or "shield" in item.name.lower():
                return "shield"
            return "weapon"
        if slot in slot_icons:
            return slot_icons[slot]

        type_icons = {
            "weapon": "weapon",
            "armor": "torso",
            "garment": "garment",
            "accessory": "ring",
            "consumable": "consumable",
            "container": "default",
            "resource": "resource",
            "material": "resource",
            "currency": "resource",
            "quest": "quest",
        }
        return type_icons.get(item.item_type, "default")

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
        for key in ("power", "armor", "defense", "damage"):
            if key in item.mechanics and item.mechanics[key] is not None:
                lines.append(self._line(self._base_line_key(item, key), item.mechanics[key], "neutral"))

        bonuses = item.mechanics.get("implicit_bonuses") or {}
        if isinstance(bonuses, dict):
            lines.extend(self._bonus_lines(bonuses))
        lines.extend(self._affix_lines(item.mechanics.get("affixes")))

        weight = self._weight_label(item)
        if weight != "-":
            lines.append(InventoryDetailLineDTO(label="Weight", value=weight, tone="neutral"))
        if item.quantity > 1:
            lines.append(InventoryDetailLineDTO(label="Quantity", value=str(item.quantity), tone="neutral"))
        durability = self._durability_label(item)
        if durability:
            lines.append(InventoryDetailLineDTO(label="Durability", value=durability, tone="neutral"))
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
                    value=self._display_stat_delta(key, delta),
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
        raw_effects = item.mechanics.get("effects") or item.metadata.get("effects") or []
        if isinstance(raw_effects, str):
            raw_effects = [raw_effects]
        if not isinstance(raw_effects, list):
            return []
        return [
            InventoryEffectTagDTO(label=self._label(str(effect)), tone="positive") for effect in raw_effects if effect
        ]

    def _meta_fields(self, item: InventoryRuntimeItemDTO) -> list[InventoryMetaFieldDTO]:
        fields = [InventoryMetaFieldDTO(label="Type", value=self._label(item.item_type))]
        slot = item.slot or (item.valid_slots[0] if item.valid_slots else "")
        if slot:
            fields.append(InventoryMetaFieldDTO(label="Slot", value=self._label(slot)))
        if item.metadata.get("source"):
            fields.append(InventoryMetaFieldDTO(label="Source", value=str(item.metadata["source"])))
        return fields

    def _numeric_stats(self, item: InventoryRuntimeItemDTO) -> dict[str, float]:
        stats: dict[str, float] = {}
        for key in ("power", "armor", "defense", "damage"):
            value = self._float_value(item.mechanics.get(key))
            if value is not None:
                stats[key] = value
        for source in (item.mechanics.get("implicit_bonuses"),):
            if not isinstance(source, dict):
                continue
            for key, raw in source.items():
                value = self._float_value(raw)
                if value is not None:
                    stats[str(key)] = stats.get(str(key), 0.0) + value
        for affix in self._iter_affixes(item.mechanics.get("affixes")):
            affix_id = str(affix.get("affix_id") or "")
            value = self._float_value(affix.get("value"))
            if affix_id and value is not None:
                stats[f"affix:{affix_id}"] = stats.get(f"affix:{affix_id}", 0.0) + value
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
                    value=self._display_stat_value(str(key), value),
                    tone="neutral",
                )
            )
        return lines

    @staticmethod
    def _base_line_key(item: InventoryRuntimeItemDTO, key: str) -> str:
        if item.base_id == "belt" and key == "power":
            return "inventory_cell_capacity"
        return key

    def _affix_lines(self, raw_affixes: object) -> list[InventoryDetailLineDTO]:
        lines: list[InventoryDetailLineDTO] = []
        for raw_affix in self._iter_affixes(raw_affixes):
            affix_id = str(raw_affix.get("affix_id") or "")
            entry = AFFIX_CATALOG.get(affix_id)
            value = self._float_value(raw_affix.get("value"))
            if entry is None or value is None:
                continue
            formatted_value = self._format_affix_value(entry.technical.value_kind, value)
            lines.append(
                InventoryDetailLineDTO(
                    label=entry.descriptive.display_name,
                    value=entry.descriptive.ui_template.replace("{value}", formatted_value),
                    tone="neutral",
                )
            )
        return lines

    @staticmethod
    def _iter_affixes(raw_affixes: object) -> list[dict[str, object]]:
        if not isinstance(raw_affixes, list):
            return []
        return [affix for affix in raw_affixes if isinstance(affix, dict)]

    @staticmethod
    def _format_affix_value(value_kind: str, value: float) -> str:
        if value_kind in {"probability", "multiplier_delta"}:
            return InventoryViewService._plain_number(abs(value) * 100)
        return InventoryViewService._plain_number(abs(value))

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
        width = InventoryViewService._positive_int(item.metadata.get("width_cells"))
        height = InventoryViewService._positive_int(item.metadata.get("height_cells"))
        if width <= 1 and height <= 1:
            width, height = InventoryViewService._fallback_grid_dimensions(item)

        return max(1, min(8, width)), max(1, min(4, height))

    @staticmethod
    def _fallback_grid_dimensions(item: InventoryRuntimeItemDTO) -> tuple[int, int]:
        slot = item.slot or (item.valid_slots[0] if item.valid_slots else "")
        by_base = {
            "dagger": (1, 2),
            "sword": (1, 3),
            "katana": (1, 4),
            "buckler": (2, 2),
            "shield": (2, 3),
            "leather_cap": (2, 2),
            "goggles": (2, 1),
            "chainmail": (2, 3),
            "jerkin": (2, 3),
            "brigandine": (2, 3),
            "boots": (2, 2),
            "linen_shirt": (2, 2),
            "wool_tunic": (2, 2),
            "apron": (2, 2),
            "winter_cloak": (2, 3),
            "work_gloves": (2, 1),
            "fur_pants": (2, 2),
        }
        if item.base_id in by_base:
            return by_base[item.base_id]

        by_slot = {
            EquippedSlot.HEAD_ARMOR.value: (2, 2),
            EquippedSlot.CHEST_ARMOR.value: (2, 3),
            EquippedSlot.CHEST_GARMENT.value: (2, 2),
            EquippedSlot.ARMS_ARMOR.value: (2, 1),
            EquippedSlot.GLOVES_GARMENT.value: (2, 1),
            EquippedSlot.LEGS_ARMOR.value: (2, 2),
            EquippedSlot.LEGS_GARMENT.value: (2, 2),
            EquippedSlot.FEETWEAR.value: (2, 2),
            EquippedSlot.OUTER_GARMENT.value: (2, 3),
            EquippedSlot.MAIN_HAND.value: (1, 3),
            EquippedSlot.TWO_HAND.value: (1, 4),
            EquippedSlot.OFF_HAND.value: (2, 2),
            EquippedSlot.AMULET.value: (1, 1),
            EquippedSlot.EARRING.value: (1, 1),
            EquippedSlot.RING_1.value: (1, 1),
            EquippedSlot.RING_2.value: (1, 1),
            EquippedSlot.BELT_ACCESSORY.value: (2, 1),
        }
        if slot in by_slot:
            return by_slot[slot]
        if item.item_type in {"resource", "currency", "material", "consumable", "quest"}:
            return 1, 1
        return 2, 2

    @staticmethod
    def _weight_label(item: InventoryRuntimeItemDTO) -> str:
        raw = (
            item.metadata.get("weight")
            or item.metadata.get("weight_units")
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
        labels = ["No-grade", "Common", "Uncommon", "Rare", "Epic", "Mythic", "Legendary", "Absolute"]
        return labels[InventoryViewService._rarity_tier(item)]

    @staticmethod
    def _flavor(item: InventoryRuntimeItemDTO) -> str | None:
        for key in ("flavor", "flavor_text", "lore", "lore_text"):
            raw = item.metadata.get(key)
            if raw:
                return str(raw)
        return None

    @staticmethod
    def _line(key: str, raw: object, tone: str) -> InventoryDetailLineDTO:
        value = InventoryViewService._float_value(raw)
        return InventoryDetailLineDTO(
            label=InventoryViewService._label(key),
            value=InventoryViewService._display_stat_value(key, value) if value is not None else str(raw),
            tone=tone,  # type: ignore[arg-type]
        )

    @staticmethod
    def _durability_label(item: InventoryRuntimeItemDTO) -> str | None:
        current = InventoryViewService._float_value(item.mechanics.get("durability_current"))
        maximum = InventoryViewService._float_value(item.mechanics.get("durability_max"))
        if current is None and maximum is None:
            return None
        if current is None:
            current = maximum
        if maximum is None:
            maximum = current
        if current is None or maximum is None:
            return None
        return f"{InventoryViewService._plain_number(current)}/{InventoryViewService._plain_number(maximum)}"

    @staticmethod
    def _float_value(raw: Any) -> float | None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _plain_number(value: float) -> str:
        return str(int(value)) if value.is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _display_number(value: float) -> str:
        return InventoryViewService._plain_number(abs(value))

    @staticmethod
    def _display_stat_value(key: str, value: float) -> str:
        number = abs(value)
        if InventoryViewService._is_percent_stat(key):
            return f"{InventoryViewService._plain_number(number * 100)}%"
        return InventoryViewService._plain_number(number)

    @staticmethod
    def _display_stat_delta(key: str, value: float) -> str:
        number = abs(value)
        if InventoryViewService._is_percent_stat(key):
            formatted = f"{InventoryViewService._plain_number(number * 100)}%"
            return f"+{formatted}" if value > 0 else f"-{formatted}" if value < 0 else "0%"
        return InventoryViewService._signed(value)

    @staticmethod
    def _is_percent_stat(key: str) -> bool:
        normalized = key.lower()
        if normalized in InventoryViewService._NON_PERCENT_STAT_KEYS:
            return False
        if normalized in InventoryViewService._PERCENT_STAT_KEYS:
            return True
        return normalized.endswith(
            (
                "_chance",
                "_avoidance",
                "_penalty",
                "_accuracy",
                "_penetration",
                "_damage_bonus",
            )
        )

    @staticmethod
    def _signed(value: float) -> str:
        number = InventoryViewService._plain_number(abs(value))
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
    def _positive_int(raw: Any) -> int:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0
