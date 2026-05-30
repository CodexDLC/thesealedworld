from __future__ import annotations

from typing import Any, Literal

from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG
from src.backend.features.items.services.catalog_service import ItemCatalogService
from src.shared.enums.item_enums import EquippedSlot, QuickSlot
from src.shared.schemas.inventory import (
    InventoryAccessoryRowDTO,
    InventoryAffixLineDTO,
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
    InventoryTabId,
    InventoryWindowDTO,
    InventoryWindowSlotDTO,
)

from .projection import belt_capacity, inventory_cell_capacity


class InventoryViewService:
    _RARITY_LABELS_RU = [
        "Без грейда",
        "Обычный",
        "Необычный",
        "Редкий",
        "Эпический",
        "Мифический",
        "Легендарный",
        "Абсолют",
    ]
    _ITEM_TYPE_LABELS_RU = {
        "weapon": "Оружие",
        "armor": "Броня",
        "garment": "Одежда",
        "accessory": "Аксессуар",
        "consumable": "Расходник",
        "container": "Контейнер",
        "resource": "Ресурс",
        "material": "Материал",
        "currency": "Валюта",
        "quest": "Квестовый предмет",
    }
    _STAT_LABELS_RU = {
        "agility": "Ловкость",
        "anti_crit_chance": "Защита от крита",
        "anti_dodge_chance": "Против уворота",
        "arcane_resistance": "Сопротивление тайне",
        "armor": "Броня",
        "armor_ignore_chance": "Шанс игнорирования брони",
        "armor_penetration_flat": "Пробитие брони",
        "armor_penetration_pct": "Пробитие брони",
        "bleed_damage_bonus": "Усиление кровотечения",
        "bleed_resistance": "Сопротивление кровотечению",
        "block": "Блок",
        "block_chance": "Шанс блока",
        "cold_resistance": "Сопротивление холоду",
        "control_chance": "Шанс контроля",
        "control_resistance": "Сопротивление контролю",
        "counter_attack_chance": "Шанс контратаки",
        "crafting_speed": "Скорость ремесла",
        "crit_chance": "Шанс крита",
        "damage": "Урон",
        "debuff_avoidance": "Избежание ослаблений",
        "defense": "Защита",
        "durability": "Прочность",
        "energy_max": "Максимум энергии",
        "environment_cold_resistance": "Защита от холода",
        "environment_heat_resistance": "Защита от жара",
        "evasion": "Уклонение",
        "evasion_penalty": "Штраф уклонения",
        "find_loot_chance": "Поиск добычи",
        "fire_damage_bonus": "Урон огнём",
        "fire_resistance": "Сопротивление огню",
        "heat_resistance": "Сопротивление жару",
        "hp_max": "Максимум здоровья",
        "hp_regen": "Восстановление здоровья",
        "initiative": "Инициатива",
        "intelligence": "Интеллект",
        "inventory_cell_capacity": "Ячейки инвентаря",
        "item_armor_penetration_pct": "Пробитие брони",
        "item_accuracy_penalty": "Штраф применения предмета",
        "item_crit_chance": "Шанс крита",
        "luck": "Удача",
        "magic_damage": "Магический урон",
        "magic_penetration": "Пробитие магии",
        "magic_resist": "Магическая защита",
        "magic_armor": "Магическая броня",
        "magical_damage_bonus": "Магический урон",
        "magical_penetration": "Пробитие магии",
        "magical_resistance": "Магическая защита",
        "main_hand_accuracy": "Точность основной руки",
        "main_hand_accuracy_penalty": "Штраф владения основной рукой",
        "main_hand_armor_penetration_pct": "Пробитие брони",
        "main_hand_crit_chance": "Шанс крита",
        "maximum_energy": "Максимум энергии",
        "maximum_hp": "Максимум здоровья",
        "off_hand_accuracy": "Точность второй руки",
        "off_hand_accuracy_penalty": "Штраф владения второй рукой",
        "off_hand_armor_penetration_pct": "Пробитие брони",
        "off_hand_crit_chance": "Шанс крита",
        "parry_chance": "Парирование",
        "perception": "Восприятие",
        "physical_accuracy": "Физическая точность",
        "physical_crit_chance": "Шанс крита",
        "physical_crit_power_float": "Сила крита",
        "physical_damage_bonus": "Физический урон",
        "physical_suppression": "Физическое пробитие",
        "physical_resistance": "Физическая защита",
        "power": "Сила",
        "quick_slot_capacity": "Слоты пояса",
        "resource_find": "Поиск ресурсов",
        "scouting": "Разведка",
        "shield_block_chance": "Блок щитом",
        "shield_guard_power": "Сила щита",
        "stamina_regen": "Восстановление концентрации",
        "strength": "Сила",
        "thorns_damage": "Шипы",
        "trade_bonus": "Торговля",
        "travel_speed": "Скорость пути",
        "vampiric_power": "Вампиризм",
        "vampiric_trigger_chance": "Шанс вампиризма",
        "weapon_accuracy": "Точность",
        "weapon_armor_penetration_pct": "Пробитие брони",
        "weapon_crit_chance": "Шанс крита",
    }
    _AFFIX_LABELS_RU = {
        "agility": "Ловкость",
        "arcane_resistance": "Сопротивление тайне",
        "arcane_resistance_bonus": "Сопротивление тайне",
        "attribute_agility": "Ловкость",
        "attribute_perception": "Восприятие",
        "attribute_strength": "Сила",
        "armor_flat": "Броня",
        "armor_penetration_pct_bonus": "Пробитие брони",
        "bio_resistance": "Биозащита",
        "bio_resistance_bonus": "Биозащита",
        "block_bonus": "Шанс блока",
        "cold_resistance": "Сопротивление холоду",
        "cold_resistance_bonus": "Сопротивление холоду",
        "control_chance": "Шанс контроля",
        "control_chance_bonus": "Шанс контроля",
        "control_resistance": "Сопротивление контролю",
        "control_resistance_bonus": "Сопротивление контролю",
        "crafting_speed": "Скорость ремесла",
        "crit_chance": "Шанс крита",
        "crit_power": "Сила крита",
        "evasion": "Уклонение",
        "evasion_bonus": "Уклонение",
        "en_bonus": "Максимум энергии",
        "fire_damage": "Урон огнём",
        "fire_damage_bonus": "Урон огнём",
        "fire_resistance": "Сопротивление огню",
        "fire_resistance_bonus": "Сопротивление огню",
        "heat_resistance": "Сопротивление жару",
        "heat_resistance_bonus": "Сопротивление жару",
        "hp_bonus": "Максимум здоровья",
        "hp_regen_bonus": "Восстановление здоровья",
        "hp_regeneration": "Восстановление здоровья",
        "luck": "Удача",
        "luck_bonus": "Удача",
        "magic_damage": "Магический урон",
        "magic_damage_bonus": "Магический урон",
        "magic_penetration": "Пробитие магии",
        "magic_penetration_bonus": "Пробитие магии",
        "maximum_energy": "Максимум энергии",
        "maximum_hp": "Максимум здоровья",
        "off_hand_accuracy": "Точность второй руки",
        "pathfinding": "Поиск пути",
        "pathfinding_bonus": "Поиск пути",
        "perception": "Восприятие",
        "physical_resistance_bonus": "Физическая защита",
        "resource_find": "Поиск ресурсов",
        "resource_find_chance": "Поиск ресурсов",
        "scouting": "Разведка",
        "scouting_bonus": "Разведка",
        "shield_guard_power_bonus": "Сила щита",
        "strength": "Сила",
        "thorns_damage": "Шипы",
        "thorns_damage_bonus": "Шипы",
        "trade_bonus": "Торговля",
        "travel_speed": "Скорость пути",
        "vampiric_power_bonus": "Вампиризм",
        "vampiric_trigger_chance_bonus": "Шанс вампиризма",
        "weapon_accuracy": "Точность оружия",
    }
    _SLOT_LABELS_RU = {
        "amulet": "Амулет",
        "arms_armor": "Наручи",
        "belt_accessory": "Пояс",
        "chest_armor": "Броня корпуса",
        "chest_garment": "Одежда корпуса",
        "earring": "Серьги",
        "feetwear": "Обувь",
        "gloves_garment": "Перчатки",
        "head_armor": "Голова",
        "legs_armor": "Поножи",
        "legs_garment": "Штаны",
        "main_hand": "Основная",
        "off_hand": "Вторая",
        "outer_garment": "Плащ",
        "quiver": "Колчан",
        "ring_1": "Кольцо 1",
        "ring_2": "Кольцо 2",
        "two_hand": "Две руки",
    }
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
        "anti_crit_chance",
        "anti_dodge_chance",
        "armor_ignore_chance",
        "armor_penetration_pct",
        "item_armor_penetration_pct",
        "item_accuracy_penalty",
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
        "main_hand_accuracy_penalty",
        "main_hand_armor_penetration_pct",
        "main_hand_crit_chance",
        "magical_damage_bonus",
        "magical_penetration",
        "magical_resistance",
        "magic_resist",
        "off_hand_accuracy",
        "off_hand_accuracy_penalty",
        "off_hand_armor_penetration_pct",
        "off_hand_crit_chance",
        "parry_chance",
        "physical_accuracy",
        "physical_crit_chance",
        "physical_crit_power_float",
        "physical_damage_bonus",
        "physical_suppression",
        "physical_resistance",
        "phys_accuracy",
        "phys_resist",
        "shield_block_chance",
        "shock_resistance",
        "thorns_damage_reflect",
        "vampiric_power",
        "water_resistance",
        "weapon_accuracy",
        "weapon_armor_penetration_pct",
        "weapon_crit_chance",
    }

    def __init__(self, catalog: ItemCatalogService | None = None) -> None:
        self.catalog = catalog or ItemCatalogService.load_default()

    def build_window(
        self,
        session: InventoryRuntimeSessionDTO,
        *,
        can_act: bool,
        active_tab: InventoryTabId = "items",
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
                self._zone(session, "head", "Голова", EquippedSlot.HEAD_ARMOR.value, "Шлем", "armor", "head"),
                self._zone(session, "outer", "Плащ", EquippedSlot.OUTER_GARMENT.value, "Плащ", "garment", "outer"),
                self._zone(
                    session,
                    "chest",
                    "Корпус",
                    EquippedSlot.CHEST_ARMOR.value,
                    "Броня",
                    "armor",
                    "chest",
                    secondary=(EquippedSlot.CHEST_GARMENT.value, "Одежда", "garment"),
                ),
                self._zone(
                    session,
                    "arms",
                    "Руки",
                    EquippedSlot.ARMS_ARMOR.value,
                    "Наручи",
                    "armor",
                    "arms",
                    secondary=(EquippedSlot.GLOVES_GARMENT.value, "Перчатки", "garment"),
                ),
                self._zone(
                    session,
                    "legs",
                    "Ноги",
                    EquippedSlot.LEGS_ARMOR.value,
                    "Поножи",
                    "armor",
                    "legs",
                    secondary=(EquippedSlot.LEGS_GARMENT.value, "Штаны", "garment"),
                ),
                self._zone(session, "feet", "Обувь", EquippedSlot.FEETWEAR.value, "Обувь", "equipment", "feet"),
            ],
            weapon_slots=self._weapon_slots(session),
            accessory_rows=[
                InventoryAccessoryRowDTO(
                    row_id="amulet",
                    label="Амулет",
                    slots=[self._slot(session, EquippedSlot.AMULET.value, "Амулет", "accessory")],
                ),
                InventoryAccessoryRowDTO(
                    row_id="earrings",
                    label="Серьги",
                    slots=[self._slot(session, EquippedSlot.EARRING.value, "Серьги", "accessory")],
                ),
                InventoryAccessoryRowDTO(
                    row_id="rings",
                    label="Кольца",
                    slots=[
                        self._slot(session, EquippedSlot.RING_1.value, "Кольцо 1", "accessory"),
                        self._slot(session, EquippedSlot.RING_2.value, "Кольцо 2", "accessory"),
                    ],
                    is_wide=False,
                ),
                InventoryAccessoryRowDTO(
                    row_id="belt",
                    label="Пояс",
                    slots=[self._slot(session, EquippedSlot.BELT_ACCESSORY.value, "Пояс", "accessory")],
                ),
                InventoryAccessoryRowDTO(
                    row_id="quiver",
                    label="Колчан",
                    slots=[self._slot(session, EquippedSlot.QUIVER.value, "Колчан", "accessory")],
                ),
            ],
            quick_slots=self._quick_slots(session),
            tabs=self._tabs(active_tab),
            visible_rows=self._rows(session, active_tab=active_tab),
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

    def _weapon_slots(self, session: InventoryRuntimeSessionDTO) -> list[InventoryWindowSlotDTO]:
        if self._item_in_equipment_slot(session, EquippedSlot.TWO_HAND.value):
            return [self._slot(session, EquippedSlot.TWO_HAND.value, "Две руки", "equipment")]
        return [
            self._slot(session, EquippedSlot.MAIN_HAND.value, "Основная", "equipment"),
            self._slot(session, EquippedSlot.OFF_HAND.value, "Вторая", "equipment"),
        ]

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

    def _rows(
        self, session: InventoryRuntimeSessionDTO, active_tab: InventoryTabId = "items"
    ) -> list[InventoryContainerRowDTO]:
        rows: list[InventoryContainerRowDTO] = []
        for item in session.by_id.values():
            if item.placement != "backpack":
                continue
            grid_w, grid_h = self._grid_dimensions(item)
            details = self._item_details(session, item)
            row = InventoryContainerRowDTO(
                item_id=item.item_id,
                icon=self._icon_key(item),
                name=item.name,
                item_type=item.item_type,
                filter_group=self._filter_group(item.item_type),
                weight=self._weight_label(item),
                quantity=item.quantity,
                rarity=item.rarity,
                rarity_tier=details.rarity_tier,
                rarity_label=details.rarity_label,
                equip_target=self._equip_target(session, item),
                valid_slots=item.valid_slots,
                grid_w=grid_w,
                grid_h=grid_h,
                is_equipped=item.placement == "equipped",
                sync_state=item.sync_state,
                is_unsecured=item.is_unsecured,
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
            if row.filter_group == active_tab:
                rows.append(row)
        rows.extend(self._wallet_rows(session, active_tab=active_tab))
        return rows

    def _wallet_rows(
        self, session: InventoryRuntimeSessionDTO, active_tab: InventoryTabId = "items"
    ) -> list[InventoryContainerRowDTO]:
        if active_tab != "resources":
            return []
        rows: list[InventoryContainerRowDTO] = []
        rows.extend(self._wallet_bucket_rows(session.wallet.currency, item_type="currency", rarity="currency"))
        rows.extend(self._wallet_bucket_rows(session.wallet.resources, item_type="resource", rarity="resource"))
        rows.extend(self._wallet_bucket_rows(session.wallet.components, item_type="material", rarity="component"))
        return rows

    @staticmethod
    def _tabs(active_tab: InventoryTabId) -> list[InventoryTabDTO]:
        return [
            InventoryTabDTO(tab_id="items", label="Предметы", icon="I", is_active=active_tab == "items"),
            InventoryTabDTO(tab_id="resources", label="Ресурсы", icon="R", is_active=active_tab == "resources"),
            InventoryTabDTO(tab_id="quest", label="Квест", icon="Q", is_active=active_tab == "quest"),
        ]

    def _wallet_bucket_rows(
        self,
        bucket: dict[str, int],
        *,
        item_type: str,
        rarity: str,
    ) -> list[InventoryContainerRowDTO]:
        rows: list[InventoryContainerRowDTO] = []
        for resource_key, raw_amount in sorted(bucket.items()):
            try:
                amount = int(raw_amount)
            except (TypeError, ValueError):
                continue
            if amount <= 0:
                continue
            details = self._resource_details(resource_key, item_type=item_type, amount=amount, rarity=rarity)
            rows.append(
                InventoryContainerRowDTO(
                    item_id=f"wallet:{resource_key}",
                    icon=self._resource_icon_key(resource_key, item_type=item_type),
                    name=details.name,
                    item_type=item_type,
                    filter_group="resources",
                    weight="-",
                    quantity=amount,
                    rarity=rarity,
                    rarity_tier=0,
                    rarity_label=details.rarity_label,
                    grid_w=1,
                    grid_h=1,
                    details=details,
                )
            )
        return rows

    def _resource_details(
        self,
        resource_key: str,
        *,
        item_type: str,
        amount: int,
        rarity: str,
    ) -> InventoryItemDetailsDTO:
        resource = self.catalog.get_raw_resource(resource_key)
        material = self.catalog.get_material(resource_key)
        name = resource.name_ru if resource is not None else material.name_ru if material is not None else resource_key
        description = (
            resource.narrative_description
            if resource is not None
            else material.narrative_description
            if material is not None and material.narrative_description
            else ""
        )
        return InventoryItemDetailsDTO(
            item_id=f"wallet:{resource_key}",
            name=name,
            item_type=item_type,
            item_type_label=self._item_type_label(item_type),
            rarity=rarity,
            rarity_tier=0,
            rarity_label=self._rarity_label_from_key(rarity),
            description=description,
            details=[InventoryDetailLineDTO(label="Количество", value=str(amount), tone="neutral")],
            meta=[InventoryMetaFieldDTO(label="Тип", value=self._item_type_label(item_type))],
        )

    def _icon_key(self, item: InventoryRuntimeItemDTO) -> str:
        slot = item.slot or (item.valid_slots[0] if item.valid_slots else "")
        if item.item_type == "weapon":
            return self._weapon_icon_key(item)
        base_icons = {
            "scout_leggings": "legs_light",
            "breeches": "legs_medium",
            "greaves": "legs_heavy",
            "fur_pants": "legwear",
            "travel_boots": "feetwear",
        }
        if item.base_id in base_icons:
            return base_icons[item.base_id]
        slot_icons = {
            EquippedSlot.HEAD_ARMOR.value: "head",
            EquippedSlot.OUTER_GARMENT.value: "cloak",
            EquippedSlot.CHEST_ARMOR.value: "torso",
            EquippedSlot.CHEST_GARMENT.value: "garment",
            EquippedSlot.ARMS_ARMOR.value: "arms",
            EquippedSlot.GLOVES_GARMENT.value: "arms",
            EquippedSlot.LEGS_ARMOR.value: "legs",
            EquippedSlot.LEGS_GARMENT.value: "legwear",
            EquippedSlot.FEETWEAR.value: "feetwear",
            EquippedSlot.MAIN_HAND.value: "weapon",
            EquippedSlot.TWO_HAND.value: "weapon",
            EquippedSlot.AMULET.value: "amulet",
            EquippedSlot.EARRING.value: "earrings",
            EquippedSlot.RING_1.value: "ring",
            EquippedSlot.RING_2.value: "ring",
            EquippedSlot.BELT_ACCESSORY.value: "belt",
            EquippedSlot.QUIVER.value: "quiver",
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

    def _resource_icon_key(self, resource_key: str, *, item_type: str) -> str:
        if item_type == "currency":
            return "resource_currency"

        entry = self.catalog.by_id(resource_key)
        category = str(entry.category).lower() if entry is not None and entry.category else ""
        category_icons = {
            "currency": "resource_currency",
            "essences": "resource_essence",
            "ores": "resource_ore",
            "ingots": "resource_ore",
            "stone": "resource_stone",
            "woods": "resource_wood",
            "bark": "resource_wood",
            "fibers": "resource_fiber",
            "cloths": "resource_fiber",
            "flowers": "resource_flower",
            "hides": "resource_hide",
            "leathers": "resource_hide",
            "parts": "resource_parts",
            "common_supplies": "resource_parts",
        }
        if category in category_icons:
            return category_icons[category]
        if item_type == "material":
            return "resource_parts"
        return "resource"

    @staticmethod
    def _filter_group(item_type: str) -> Literal["items", "resources", "quest"]:
        if item_type in {"resource", "currency", "material"}:
            return "resources"
        if item_type == "quest":
            return "quest"
        return "items"

    @staticmethod
    def _weapon_icon_key(item: InventoryRuntimeItemDTO) -> str:
        base_id = item.base_id.lower()
        tags = {str(tag).lower() for tag in item.tags}
        haystack = {base_id, *tags}
        if base_id in {"greatsword", "katana"} or "two_handed" in haystack:
            return "weapon_two_hand"
        if haystack & {"bow", "archery", "ranged", "shortbow", "sling"}:
            return "weapon_bow"
        if haystack & {"dagger", "knife", "stiletto", "main_gauche", "katar"}:
            return "weapon_dagger"
        if haystack & {"axe", "hatchet", "battle_axe", "chop"}:
            return "weapon_axe"
        if haystack & {"hammer", "warhammer"}:
            return "weapon_hammer"
        if haystack & {"mace", "flail", "blunt", "macing"}:
            return "weapon_mace"
        if "halberd" in haystack:
            return "weapon_halberd"
        if "quarterstaff" in haystack or "staff" in haystack:
            return "weapon_staff"
        if "trident" in haystack:
            return "weapon_trident"
        if "pike" in haystack:
            return "weapon_pike"
        if "spear" in haystack:
            return "weapon_spear"
        if "polearm" in haystack:
            return "weapon_polearm"
        if haystack & {"sword", "longsword", "scimitar", "rapier", "blade", "fast_blade"}:
            return "weapon_sword"
        return "weapon"

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
            item_type_label=self._item_type_label(item.item_type),
            rarity=item.rarity,
            rarity_tier=self._rarity_tier(item),
            rarity_label=self._rarity_label(item),
            description=item.description,
            flavor=self._flavor(item),
            details=self._detail_lines(item),
            affixes=self._affix_lines(item.mechanics.get("affixes"), fallback_tier=self._rarity_tier(item)),
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
        target_slot = self._equip_target(session, item)
        if target_slot:
            equipped_id = session.layout.equipment.get(target_slot)
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

        weight = self._weight_label(item)
        if weight != "-":
            lines.append(InventoryDetailLineDTO(label="Вес", value=weight, tone="neutral"))
        if item.quantity > 1:
            lines.append(InventoryDetailLineDTO(label="Количество", value=str(item.quantity), tone="neutral"))
        durability = self._durability_label(item)
        if durability:
            lines.append(InventoryDetailLineDTO(label="Прочность", value=durability, tone="neutral"))
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
        equip_target = self._equip_target(session, item)
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
        actions.append(InventoryItemActionDTO(action="drop", label="Выбросить", style="danger"))
        return actions

    @staticmethod
    def _equip_target(session: InventoryRuntimeSessionDTO, item: InventoryRuntimeItemDTO) -> str | None:
        valid_slots = item.valid_slots or ([item.slot] if item.slot else [])
        if not valid_slots:
            return None

        for slot_id in valid_slots:
            if not session.layout.equipment.get(slot_id):
                return slot_id

        primary_slot = item.slot or item.mechanics.get("slot")
        if isinstance(primary_slot, str) and primary_slot in valid_slots:
            return primary_slot
        return valid_slots[0]

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
        fields = [InventoryMetaFieldDTO(label="Тип", value=self._item_type_label(item.item_type))]
        slot = item.slot or (item.valid_slots[0] if item.valid_slots else "")
        if slot:
            fields.append(InventoryMetaFieldDTO(label="Слот", value=self._label(slot)))
        if item.metadata.get("source"):
            fields.append(InventoryMetaFieldDTO(label="Источник", value=str(item.metadata["source"])))
        return fields

    def _numeric_stats(self, item: InventoryRuntimeItemDTO) -> dict[str, float]:
        stats: dict[str, float] = {}
        for key in ("power", "armor", "defense", "damage"):
            value = self._float_value(item.mechanics.get(key))
            if value is not None:
                stats[self._base_line_key(item, key)] = value
        for source in (item.mechanics.get("implicit_bonuses"),):
            if not isinstance(source, dict):
                continue
            for key, raw in source.items():
                if key == "accuracy_penalty":
                    continue
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
            if key == "accuracy_penalty":
                continue
            value = self._float_value(raw)
            if value is None:
                lines.append(InventoryDetailLineDTO(label=self._label(key), value=str(raw), tone="neutral"))
                continue
            lines.append(
                InventoryDetailLineDTO(
                    label=self._label(key),
                    value=self._display_stat_value(key, value),
                    tone="neutral",
                )
            )
        return lines

    @staticmethod
    def _base_line_key(item: InventoryRuntimeItemDTO, key: str) -> str:
        if key != "power":
            return key
        if item.base_id == "belt":
            return "inventory_cell_capacity"
        if item.item_type == "weapon":
            return "damage"
        if item.item_type == "armor":
            return "armor"
        if item.item_type == "garment":
            return "defense"
        return "power"

    def _affix_lines(self, raw_affixes: object, *, fallback_tier: int = 0) -> list[InventoryAffixLineDTO]:
        lines: list[InventoryAffixLineDTO] = []
        for raw_affix in self._iter_affixes(raw_affixes):
            affix_id = str(raw_affix.get("affix_id") or "")
            entry = AFFIX_CATALOG.get(affix_id)
            value = self._float_value(raw_affix.get("value"))
            if entry is None or value is None:
                continue
            formatted_value = self._format_affix_value(entry.technical.value_kind, value)
            lines.append(
                InventoryAffixLineDTO(
                    affix_id=affix_id,
                    label=self._affix_label(affix_id, entry.descriptive.display_name),
                    value=self._format_affix_text(entry.descriptive.ui_template, formatted_value),
                    tier=self._affix_tier(raw_affix, fallback_tier),
                    source=str(raw_affix.get("source") or "") or None,
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
            "jerkin": (2, 3),
            "reinforced_gloves": (2, 2),
            "soft_bracers": (2, 2),
            "scout_leggings": (2, 2),
            "travel_boots": (2, 2),
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
            EquippedSlot.QUIVER.value: (1, 2),
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
        return InventoryViewService._RARITY_LABELS_RU[InventoryViewService._rarity_tier(item)]

    @staticmethod
    def _rarity_label_from_key(rarity: str) -> str:
        labels = {
            "currency": "Валюта",
            "resource": "Ресурс",
            "component": "Компонент",
        }
        return labels.get(rarity, rarity)

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
                "_pct",
                "_damage_bonus",
            )
        )

    @staticmethod
    def _signed(value: float) -> str:
        number = InventoryViewService._plain_number(abs(value))
        return f"+{number}" if value > 0 else f"-{number}" if value < 0 else "0"

    @staticmethod
    def _label(key: str) -> str:
        normalized = key.replace("-", "_").lower()
        if normalized in InventoryViewService._STAT_LABELS_RU:
            return InventoryViewService._STAT_LABELS_RU[normalized]
        if normalized in InventoryViewService._SLOT_LABELS_RU:
            return InventoryViewService._SLOT_LABELS_RU[normalized]
        if normalized in InventoryViewService._ITEM_TYPE_LABELS_RU:
            return InventoryViewService._ITEM_TYPE_LABELS_RU[normalized]
        return key.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _item_type_label(item_type: str) -> str:
        return InventoryViewService._ITEM_TYPE_LABELS_RU.get(item_type, InventoryViewService._label(item_type))

    @staticmethod
    def _affix_label(affix_id: str, fallback: str) -> str:
        return InventoryViewService._AFFIX_LABELS_RU.get(affix_id, InventoryViewService._label(fallback))

    @staticmethod
    def _format_affix_text(template: str, formatted_value: str) -> str:
        suffix = "%" if "%" in template else ""
        return f"+{formatted_value}{suffix}"

    @staticmethod
    def _affix_tier(raw_affix: dict[str, object], fallback_tier: int) -> int:
        for key in ("tier", "affix_tier", "item_tier"):
            val = raw_affix.get(key)
            if val is not None:
                try:
                    return max(0, min(7, int(val)))  # type: ignore[arg-type, call-overload]
                except (TypeError, ValueError):
                    continue
        return max(0, min(7, fallback_tier))

    @staticmethod
    def _is_quick_slot_compatible(item: InventoryRuntimeItemDTO) -> bool:
        return bool(item.mechanics.get("is_quick_slot_compatible"))

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
