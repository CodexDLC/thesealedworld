from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.backend.core.calculators.stats_waterfall_calculator import StatsWaterfallCalculator
from src.backend.features.character.runtime.rules.attribute_modifiers import DEFAULT_MODIFIER_VALUES
from src.backend.features.character.runtime.rules.vital_constants import REGEN_TICK_SECONDS
from src.backend.features.character.schemas.session import (
    CharacterSessionAttributesDTO,
    CharacterSessionVitalsDTO,
    VitalValueDTO,
)


@dataclass(frozen=True)
class VitalFormulaResult:
    max: int
    regen: float


class CharacterVitalsCalculator:
    """Builds AC vitals from character attributes while keeping current values separate."""

    @classmethod
    def build_initial_vitals(
        cls,
        attributes: CharacterSessionAttributesDTO,
        *,
        profile_key: str = "player",
        items: dict[str, Any] | None = None,
    ) -> CharacterSessionVitalsDTO:
        max_vitals = cls.calculate_max_vitals(attributes, profile_key=profile_key, items=items)
        return CharacterSessionVitalsDTO(
            hp=VitalValueDTO(cur=max_vitals.hp.max, max=max_vitals.hp.max, regen=max_vitals.hp.regen),
            energy=VitalValueDTO(
                cur=max_vitals.energy.max,
                max=max_vitals.energy.max,
                regen=max_vitals.energy.regen,
            ),
            stamina=VitalValueDTO(
                cur=max_vitals.stamina.max,
                max=max_vitals.stamina.max,
                regen=max_vitals.stamina.regen,
            ),
        )

    @classmethod
    def build_vitals_from_snapshot(
        cls,
        snapshot: dict[str, Any] | None,
        attributes: CharacterSessionAttributesDTO,
        *,
        profile_key: str = "player",
        items: dict[str, Any] | None = None,
    ) -> CharacterSessionVitalsDTO:
        if not snapshot:
            return cls.build_initial_vitals(attributes, profile_key=profile_key, items=items)

        snapshot_vitals = CharacterSessionVitalsDTO.model_validate(snapshot)
        return cls.refresh_max_vitals(snapshot_vitals, attributes, profile_key=profile_key, items=items)

    @classmethod
    def refresh_max_vitals(
        cls,
        current_vitals: CharacterSessionVitalsDTO,
        attributes: CharacterSessionAttributesDTO,
        *,
        profile_key: str = "player",
        fill_if_default: bool = False,
        items: dict[str, Any] | None = None,
    ) -> CharacterSessionVitalsDTO:
        max_vitals = cls.calculate_max_vitals(attributes, profile_key=profile_key, items=items)
        all_default = cls._is_default_vitals(current_vitals)

        return CharacterSessionVitalsDTO(
            hp=cls._merge_current(current_vitals.hp, max_vitals.hp, fill_current=fill_if_default and all_default),
            energy=cls._merge_current(
                current_vitals.energy,
                max_vitals.energy,
                fill_current=fill_if_default and all_default,
            ),
            stamina=cls._merge_current(
                current_vitals.stamina,
                max_vitals.stamina,
                fill_current=fill_if_default and all_default,
            ),
            last_update=current_vitals.last_update,
        )

    @classmethod
    def restore_to_max_vitals(
        cls,
        attributes: CharacterSessionAttributesDTO,
        *,
        profile_key: str = "player",
        items: dict[str, Any] | None = None,
    ) -> CharacterSessionVitalsDTO:
        max_vitals = cls.calculate_max_vitals(attributes, profile_key=profile_key, items=items)
        now = datetime.now(UTC).timestamp()
        return CharacterSessionVitalsDTO(
            hp=VitalValueDTO(cur=max_vitals.hp.max, max=max_vitals.hp.max, regen=max_vitals.hp.regen),
            energy=VitalValueDTO(
                cur=max_vitals.energy.max,
                max=max_vitals.energy.max,
                regen=max_vitals.energy.regen,
            ),
            stamina=VitalValueDTO(
                cur=max_vitals.stamina.max,
                max=max_vitals.stamina.max,
                regen=max_vitals.stamina.regen,
            ),
            last_update=now,
        )

    @classmethod
    def calculate_max_vitals(
        cls,
        attributes: CharacterSessionAttributesDTO,
        *,
        profile_key: str = "player",
        items: dict[str, Any] | None = None,
    ) -> CharacterSessionVitalsDTO:
        calculated, _ = StatsWaterfallCalculator.calculate_waterfall(
            {
                "attributes": cls._raw_attributes(attributes),
                "modifiers": cls._base_modifiers(items),
                "rules": {"attribute_profile": profile_key},
            }
        )

        hp = cls._resource_max(calculated.get("hp", 0.0))
        energy = cls._resource_max(calculated.get("en", 0.0))
        stamina = cls._resource_max(calculated.get("stamina", 0.0))

        return CharacterSessionVitalsDTO(
            hp=VitalValueDTO(cur=hp, max=hp, regen=round(float(calculated.get("hp_regen", 0.0) or 0.0), 4)),
            energy=VitalValueDTO(cur=energy, max=energy, regen=round(float(calculated.get("en_regen", 0.0) or 0.0), 4)),
            stamina=VitalValueDTO(
                cur=stamina,
                max=stamina,
                regen=round(float(calculated.get("stamina_regen", 0.0) or 0.0), 4),
            ),
        )

    @classmethod
    def apply_regen(cls, vitals: CharacterSessionVitalsDTO, *, now: float | None = None) -> CharacterSessionVitalsDTO:
        now = now if now is not None else datetime.now(UTC).timestamp()
        if vitals.last_update <= 0:
            vitals.last_update = now
            return vitals

        elapsed = now - vitals.last_update
        tick_count = int(elapsed // REGEN_TICK_SECONDS)
        if tick_count <= 0:
            return vitals

        changed = False
        for attr_name in ("hp", "energy", "stamina"):
            value = getattr(vitals, attr_name)
            if value.cur < value.max and value.regen > 0:
                new_value = min(value.max, int(value.cur + value.regen * tick_count))
                if new_value != value.cur:
                    value.cur = new_value
                    changed = True

        if changed or cls._is_full(vitals):
            vitals.last_update += tick_count * REGEN_TICK_SECONDS
        return vitals

    @staticmethod
    def _merge_current(current: VitalValueDTO, calculated: VitalValueDTO, *, fill_current: bool) -> VitalValueDTO:
        current_value = calculated.max if fill_current else max(0, min(int(current.cur), calculated.max))
        return VitalValueDTO(cur=current_value, max=calculated.max, regen=calculated.regen)

    @staticmethod
    def _resource_max(value: float) -> int:
        return max(1, int(round(value)))

    @staticmethod
    def _raw_attributes(attributes: CharacterSessionAttributesDTO) -> dict[str, dict[str, Any]]:
        return {
            key: {"base": float(value or 0), "source": {}, "temp": {}}
            for key, value in attributes.model_dump(mode="json").items()
        }

    @staticmethod
    def _base_modifiers(items: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
        modifiers = {
            key: {"base": float(value or 0.0), "source": {}, "temp": {}}
            for key, value in DEFAULT_MODIFIER_VALUES.items()
        }
        # implicit bonuses → base layer (numeric values)
        for key, value in CharacterVitalsCalculator._equipped_item_implicit_vital_bonuses(items).items():
            modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
            modifiers[key]["base"] = round(float(modifiers[key].get("base", 0.0) or 0.0) + value, 4)
        # compiled affix bonuses → source layer (command strings)
        CharacterVitalsCalculator._apply_equipped_item_compiled_bonuses(modifiers, items)
        return modifiers

    @staticmethod
    def _equipped_item_implicit_vital_bonuses(items: dict[str, Any] | None) -> dict[str, float]:
        """Collect numeric implicit_bonuses from equipped items (base/material intrinsic stats)."""
        payload = CharacterVitalsCalculator._as_dict(items)
        layout = CharacterVitalsCalculator._as_dict(payload.get("layout"))
        equipment = CharacterVitalsCalculator._as_dict(layout.get("equipment"))
        by_id = CharacterVitalsCalculator._as_dict(payload.get("by_id"))
        totals: dict[str, float] = {}

        for item_id in equipment.values():
            if not item_id:
                continue
            item = CharacterVitalsCalculator._as_dict(by_id.get(str(item_id)))
            if not item:
                continue
            mechanics = CharacterVitalsCalculator._as_dict(item.get("mechanics"))
            bonuses = CharacterVitalsCalculator._as_dict(mechanics.get("implicit_bonuses"))
            for raw_key, raw_value in bonuses.items():
                key = CharacterVitalsCalculator._normalize_vital_modifier_key(str(raw_key))
                if key is None:
                    continue
                try:
                    numeric = float(raw_value or 0.0)
                except (TypeError, ValueError):
                    continue
                if numeric == 0:
                    continue
                totals[key] = round(float(totals.get(key, 0.0) or 0.0) + numeric, 4)
        return totals

    @staticmethod
    def _apply_equipped_item_compiled_bonuses(
        modifiers: dict[str, dict[str, Any]],
        items: dict[str, Any] | None,
    ) -> None:
        """Apply compiled affix bonuses (command strings) to the source layer."""
        payload = CharacterVitalsCalculator._as_dict(items)
        layout = CharacterVitalsCalculator._as_dict(payload.get("layout"))
        equipment = CharacterVitalsCalculator._as_dict(layout.get("equipment"))
        by_id = CharacterVitalsCalculator._as_dict(payload.get("by_id"))

        for item_id in equipment.values():
            if not item_id:
                continue
            item = CharacterVitalsCalculator._as_dict(by_id.get(str(item_id)))
            if not item:
                continue
            mechanics = CharacterVitalsCalculator._as_dict(item.get("mechanics"))
            bonuses = CharacterVitalsCalculator._as_dict(mechanics.get("bonuses"))
            if not bonuses:
                continue
            item_source = f"item:{item.get('item_id') or item_id}"
            for raw_key, raw_value in bonuses.items():
                key = CharacterVitalsCalculator._normalize_vital_modifier_key(str(raw_key))
                if key is None:
                    continue
                modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
                modifiers[key]["source"][f"{item_source}:bonus:{raw_key}"] = raw_value

    @staticmethod
    def _normalize_vital_modifier_key(raw_key: str) -> str | None:
        key = {
            "energy_max": "en",
            "en_max": "en",
            "en_add": "en",
            "hp_max": "hp",
            "hp_add": "hp",
            "maximum_hp": "hp",
            "hp_regeneration": "hp_regen",
            "hp_regen_add": "hp_regen",
            "hp_regen_bonus": "hp_regen",
            "energy_regen": "en_regen",
            "en_regeneration": "en_regen",
            "en_regen_add": "en_regen",
            "stamina_max": "stamina",
            "stamina_add": "stamina",
            "stamina_regen_add": "stamina_regen",
        }.get(raw_key, raw_key)
        return key if key in {"hp", "hp_regen", "en", "en_regen", "stamina", "stamina_regen"} else None

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return dict(value) if isinstance(value, Mapping) else {}

    @staticmethod
    def _is_default_vitals(vitals: CharacterSessionVitalsDTO) -> bool:
        return (
            vitals.hp.cur == 100
            and vitals.hp.max == 100
            and vitals.energy.cur == 100
            and vitals.energy.max == 100
            and vitals.stamina.cur == 100
            and vitals.stamina.max == 100
        )

    @staticmethod
    def _is_full(vitals: CharacterSessionVitalsDTO) -> bool:
        return (
            vitals.hp.cur >= vitals.hp.max
            and vitals.energy.cur >= vitals.energy.max
            and vitals.stamina.cur >= vitals.stamina.max
        )
