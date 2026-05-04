from typing import Any

from pydantic import BaseModel, computed_field

from src.backend.domains.internal_systems.context_assembler.schemas.base import BaseTempContext
from src.backend.domains.internal_systems.context_assembler.utils import format_value
from src.backend.resources.game_data import get_all_feints
from src.backend.resources.game_data.common.stats_enum import PrimaryStat
from src.backend.resources.game_data.items import get_weapon_trigger
from src.shared.schemas.modifier_dto import (
    DefensiveStatsDTO,
    ElementalStatsDTO,
    EnvironmentalStatsDTO,
    MagicalStatsDTO,
    MainHandStatsDTO,
    MitigationStatsDTO,
    OffHandStatsDTO,
    PhysicalStatsDTO,
    SpecialStatsDTO,
)

# Статы, которые зависят от руки (нуждаются в префиксе main_hand_ / off_hand_)
HAND_DEPENDENT_STATS = {
    "damage_base",
    "damage_spread",
    "damage_bonus",
    "penetration",
    "accuracy",
    "crit_chance",
}

# Список DTO, поля которых должны быть в modifiers
MODIFIER_DTOS: list[type[BaseModel]] = [
    MainHandStatsDTO,
    OffHandStatsDTO,
    PhysicalStatsDTO,
    MagicalStatsDTO,
    DefensiveStatsDTO,
    MitigationStatsDTO,
    ElementalStatsDTO,
    SpecialStatsDTO,
    EnvironmentalStatsDTO,
]


class CombatTempContext(BaseTempContext):
    """
    Контекст для боевой системы (RBC v3).
    Генерирует math_model (raw), skills, loadout, vitals.
    """

    @computed_field(alias="math_model")
    def combat_view(self) -> dict[str, Any]:
        """
        Проекция для COMBAT SERVICE (Raw Data).
        Содержит только attributes и modifiers.
        Skills вынесены в отдельное поле.
        """
        model: dict[str, Any] = {
            "attributes": {},
            "modifiers": {},
        }

        # 1. Attributes Base
        if self.core_attributes:
            stats_dict = self.core_attributes.model_dump()
            for stat_enum in PrimaryStat:
                key = stat_enum.value
                val = stats_dict.get(key, 0)
                model["attributes"][key] = {
                    "base": float(val),
                    "source": {},
                    "temp": {},
                }

        # 2. Modifiers Initialization (Заполняем нулями все возможные поля)
        for dto_class in MODIFIER_DTOS:
            for field_name in dto_class.model_fields:  # type: ignore
                if field_name not in model["modifiers"]:
                    model["modifiers"][field_name] = {
                        "base": 0.0,
                        "source": {},
                        "temp": {},
                    }

        # 3. Equipment Bonuses
        if self.core_inventory:
            for item in self.core_inventory:
                item_data = item.model_dump() if hasattr(item, "model_dump") else item

                if item_data.get("location") != "equipped":
                    continue

                item_id = item_data.get("item_id")
                src_key = f"item:{item_id}"

                equipped_slot = item_data.get("equipped_slot")
                prefix = ""
                if equipped_slot == "main_hand":
                    prefix = "main_hand_"
                elif equipped_slot == "off_hand":
                    prefix = "off_hand_"

                data_json = item_data.get("data") or {}
                subtype = item_data.get("subtype")

                # --- A. Explicit Fields ---
                power = data_json.get("power")
                if power is not None:
                    if item_data.get("item_type") == "weapon":
                        self._add_modifier(model, f"{prefix}damage_base", src_key, power)
                    elif item_data.get("item_type") == "armor":
                        self._add_modifier(model, "damage_reduction_flat", src_key, power)

                spread = data_json.get("spread")
                if spread is not None:
                    self._add_modifier(model, f"{prefix}damage_spread", src_key, spread)

                accuracy = data_json.get("accuracy")
                if accuracy is not None:
                    self._add_modifier(model, f"{prefix}accuracy", src_key, accuracy)

                crit = data_json.get("crit_chance")
                if crit is not None:
                    self._add_modifier(model, f"{prefix}crit_chance", src_key, crit)

                parry = data_json.get("parry_chance")
                if parry is not None:
                    if subtype == "shield":
                        self._add_modifier(model, "shield_block_chance", src_key, parry)
                    else:
                        self._add_modifier(model, "parry_chance", src_key, parry)

                block = data_json.get("block_chance")
                if block is not None:
                    self._add_modifier(model, "shield_block_chance", src_key, block)

                evasion_pen = data_json.get("evasion_penalty")
                if evasion_pen is not None:
                    self._add_modifier(model, "dodge_chance", src_key, f"{-evasion_pen}")

                dodge_cap_mod = data_json.get("dodge_cap_mod")
                if dodge_cap_mod is not None:
                    self._add_modifier(model, "dodge_cap", src_key, dodge_cap_mod)

                # --- B. Implicit Bonuses ---
                implicit = data_json.get("implicit_bonuses") or {}
                for stat, val in implicit.items():
                    final_stat = f"{prefix}{stat}" if stat in HAND_DEPENDENT_STATS else stat
                    self._add_modifier(model, final_stat, src_key, val)

                # --- C. Explicit Bonuses ---
                explicit = data_json.get("bonuses") or {}
                for stat, val in explicit.items():
                    final_stat = f"{prefix}{stat}" if stat in HAND_DEPENDENT_STATS else stat
                    self._add_modifier(model, final_stat, src_key, val)

        return model

    @computed_field(alias="skills")
    def skills_view(self) -> dict[str, float]:
        """
        Отдельное поле для скиллов.
        """
        skills: dict[str, float] = {}
        if self.core_skills:
            for skill in self.core_skills:
                if skill.total_xp > 0 or skill.is_unlocked:
                    skills[skill.skill_key] = float(skill.total_xp)
        return skills

    def _add_modifier(self, model: dict, stat_key: str, source_key: str, value: Any):
        """Helper для добавления модификатора."""
        val_str = format_value(stat_key, value, "external")

        if stat_key in model["attributes"]:
            model["attributes"][stat_key]["source"][source_key] = val_str
        else:
            if stat_key not in model["modifiers"]:
                model["modifiers"][stat_key] = {
                    "base": 0.0,
                    "source": {},
                    "temp": {},
                }
            model["modifiers"][stat_key]["source"][source_key] = val_str

    @computed_field(alias="loadout")
    def loadout_view(self) -> dict[str, Any]:
        """
        Проекция для UI/Inventory Service и Валидации.
        """
        belt = []
        equipment_layout = {}
        abilities: list[str] = []
        tags = ["player"]  # Default tag

        if self.core_inventory:
            for item in self.core_inventory:
                item_data = item.model_dump() if hasattr(item, "model_dump") else item

                if item_data.get("quick_slot_position"):
                    belt.append(item_data)

                if item_data.get("location") == "equipped":
                    slot = item_data.get("equipped_slot") or item_data.get("data", {}).get("slot") or "unknown"
                    skill_key = item_data.get("data", {}).get("related_skill")

                    # Получаем триггер атаки
                    trigger_id = None

                    # 1. Пробуем взять из item_data (если уже есть)
                    triggers = item_data.get("data", {}).get("triggers")
                    if triggers and isinstance(triggers, list) and len(triggers) > 0:
                        trigger_id = triggers[0]

                    # 2. Если нет, пробуем найти по base_id
                    if not trigger_id:
                        # Ищем base_id в components или data
                        base_id = item_data.get("components", {}).get("base_id") or item_data.get("data", {}).get(
                            "base_id"
                        )
                        if base_id:
                            trigger_id = get_weapon_trigger(base_id)

                    if skill_key:
                        equipment_layout[slot] = skill_key
                    else:
                        equipment_layout[slot] = "unknown"

                    # Сохраняем триггер в layout с суффиксом
                    if trigger_id:
                        equipment_layout[f"{slot}_trigger"] = trigger_id

        # TODO: Collect abilities from Character/Skills/Items
        # abilities = ...

        # --- FEINTS (Temporary: All Available) ---
        # TODO: Сделать маппер скиллов по навыкам актера:
        # 1. Словарь финтов по классам/типам оружия.
        # 2. Проверка активного скилла оружия.
        # 3. Учет хвата (2H, 1H+Shield, Dual Wield).
        # 4. Грязные приемы (Dirty Tricks) привязать к тактическим скиллам.
        all_feints = get_all_feints()
        known_feints = [f.feint_id for f in all_feints]

        return {
            "belt": belt,
            "abilities": abilities,
            "known_feints": known_feints,
            "equipment_layout": equipment_layout,
            "tags": tags,
        }

    @computed_field(alias="vitals")
    def vitals_view(self) -> dict[str, Any]:
        hp = 100
        en = 100
        if self.core_vitals:
            hp = self.core_vitals.get("hp", {}).get("cur", 100)
            en = self.core_vitals.get("energy", {}).get("cur", 100)
        return {"hp_current": hp, "energy_current": en}
