from typing import Any

from pydantic import BaseModel, computed_field

from src.backend.domains.internal_systems.context_assembler.utils import format_value

# Импортируем Enums для логики
from src.backend.resources.game_data.common.stats_enum import PrimaryStat

# Импортируем существующие DTO (Core Data)
from src.shared.schemas.character import CharacterAttributesReadDTO, CharacterReadDTO
from src.shared.schemas.skill import SkillProgressDTO

# Статы, которые зависят от руки (нуждаются в префиксе)
HAND_DEPENDENT_STATS = {
    "physical_damage_base",
    "physical_damage_spread",
    "physical_damage_bonus",
    "physical_penetration",
    "physical_accuracy",
    "physical_crit_chance",
    "physical_crit_power",
    "physical_crit_cap",
    "physical_pierce_chance",
    "physical_pierce_cap",
    # Можно добавить магические, если нужно
}


class TempContextSchema(BaseModel):
    """
    MASTER SCHEMA for Redis Temp Context.
    Содержит полные сырые данные + готовые проекции для систем.
    """

    # --- 1. CORE DATA (Источник правды) ---
    core_stats: CharacterAttributesReadDTO
    core_inventory: list[Any]
    core_skills: list[SkillProgressDTO]
    core_vitals: dict[str, Any]
    core_meta: CharacterReadDTO
    core_symbiote: dict[str, Any] | None = None

    # --- 2. COMPUTED VIEWS (Готовые проекции) ---

    @computed_field(alias="math_model")
    def combat_view(self) -> dict[str, Any]:
        """
        Проекция для COMBAT SERVICE (RBC Protocol).
        Чистая математика: Атрибуты и Модификаторы.
        """
        model: dict[str, Any] = {
            "attributes": {},
            "modifiers": {},
        }

        # 1. Attributes Base
        stats_dict = self.core_stats.model_dump()
        for stat_enum in PrimaryStat:
            key = stat_enum.value
            val = stats_dict.get(key, 0)
            model["attributes"][key] = {"base": str(float(val)), "flats": {}, "percents": {}}

        # 2. Equipment Bonuses
        for item in self.core_inventory:
            item_data = item.model_dump() if hasattr(item, "model_dump") else item

            # Пропускаем не надетые вещи
            loc = item_data.get("location")
            if loc != "equipped":
                continue

            item_id = item_data.get("item_id")
            src_key = f"item:{item_id}"

            # Определяем префикс руки
            equipped_slot = item_data.get("equipped_slot")
            prefix = ""
            if equipped_slot == "main_hand":
                prefix = "main_hand_"
            elif equipped_slot == "off_hand":
                prefix = "off_hand_"
            # Для 2H оружия (если оно занимает main_hand, но имеет тег 2h) - пока считаем как main_hand
            # Если нужно, можно добавить проверку subtype или tags

            # --- A. Обработка Базовых Статов Оружия (Base Power, Spread) ---
            # Эти данные лежат в item_data["data"] (JSON из базы)
            data_json = item_data.get("data") or {}  # Это поле item_data из InventoryItem

            # Если это оружие (или имеет base_power)
            base_power = data_json.get("base_power")
            if base_power is not None:
                stat_key = f"{prefix}physical_damage_base"
                self._add_modifier(model, stat_key, src_key, base_power)

            damage_spread = data_json.get("damage_spread")
            if damage_spread is not None:
                stat_key = f"{prefix}physical_damage_spread"
                self._add_modifier(model, stat_key, src_key, damage_spread)

            # --- B. Обработка Implicit Bonuses (Встроенные свойства) ---
            implicit = data_json.get("implicit_bonuses") or {}
            for stat, val in implicit.items():
                # Если стат зависимый от руки, добавляем префикс
                final_stat = f"{prefix}{stat}" if stat in HAND_DEPENDENT_STATS else stat
                self._add_modifier(model, final_stat, src_key, val)

            # --- C. Обработка Explicit Bonuses (Суффиксы/Заточка) ---
            # Обычно лежат в data["bonuses"]
            explicit = data_json.get("bonuses") or {}
            for stat, val in explicit.items():
                final_stat = f"{prefix}{stat}" if stat in HAND_DEPENDENT_STATS else stat
                self._add_modifier(model, final_stat, src_key, val)

            # --- D. Обработка Брони (Protection) ---
            # Броня обычно глобальная, префикс не нужен (или нужен defensive_?)
            protection = data_json.get("protection")
            if protection:
                self._add_modifier(model, "damage_reduction_flat", src_key, protection)

        return model

    def _add_modifier(self, model: dict, stat_key: str, source_key: str, value: Any):
        """Helper для добавления модификатора в структуру."""
        if stat_key not in model["modifiers"]:
            model["modifiers"][stat_key] = {"sources": {}}

        # Форматируем значение (превращаем в строку для simpleeval)
        val_str = format_value(stat_key, value, "external")
        model["modifiers"][stat_key]["sources"][source_key] = val_str

    @computed_field(alias="loadout")
    def loadout_view(self) -> dict[str, Any]:
        """
        Проекция для UI/Inventory Service и Валидации.
        Содержит: Пояс, Скиллы, Лейаут оружия, Теги.
        """
        belt = []
        equipment_layout = {}

        # TODO: Implement Ability Extraction Logic

        for item in self.core_inventory:
            item_data = item.model_dump() if hasattr(item, "model_dump") else item

            # Belt
            if item_data.get("quick_slot_position"):
                belt.append(item_data)

            # Layout
            if item_data.get("location") == "equipped":
                # Используем equipped_slot как приоритет
                slot = item_data.get("equipped_slot") or item_data.get("data", {}).get("slot") or "unknown"

                skill_key = item_data.get("data", {}).get("related_skill")
                if skill_key:
                    equipment_layout[slot] = skill_key
                else:
                    equipment_layout[slot] = "unknown"

        return {
            "belt": belt,
            "known_abilities": [s.skill_key for s in self.core_skills if s.is_unlocked],
            "equipment_layout": equipment_layout,
            "tags": ["player", "human"],
            "abilities": [],
        }

    @computed_field(alias="vitals")
    def vitals_view(self) -> dict[str, Any]:
        hp = 100
        en = 100
        if self.core_vitals:
            hp = self.core_vitals.get("hp", {}).get("cur", 100)
            en = self.core_vitals.get("energy", {}).get("cur", 100)
        return {"hp_current": hp, "energy_current": en}

    @computed_field(alias="meta")
    def meta_view(self) -> dict[str, Any]:
        """
        Общая мета-информация.
        """
        return {
            "entity_id": self.core_meta.character_id,
            "type": "player",
            "timestamp": 0,
            "character": {
                "name": self.core_meta.name,
                "gender": self.core_meta.gender,
                "game_stage": self.core_meta.game_stage,
                "prev_game_stage": self.core_meta.prev_game_stage,
                "location_id": self.core_meta.location_id,
                "prev_location_id": self.core_meta.prev_location_id,
            },
            "symbiote": self.core_symbiote,
        }
