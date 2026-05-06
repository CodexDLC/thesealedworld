from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

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
    def build_initial_vitals(cls, attributes: CharacterSessionAttributesDTO) -> CharacterSessionVitalsDTO:
        max_vitals = cls.calculate_max_vitals(attributes)
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
    ) -> CharacterSessionVitalsDTO:
        if not snapshot:
            return cls.build_initial_vitals(attributes)

        snapshot_vitals = CharacterSessionVitalsDTO.model_validate(snapshot)
        return cls.refresh_max_vitals(snapshot_vitals, attributes)

    @classmethod
    def refresh_max_vitals(
        cls,
        current_vitals: CharacterSessionVitalsDTO,
        attributes: CharacterSessionAttributesDTO,
        *,
        fill_if_default: bool = False,
    ) -> CharacterSessionVitalsDTO:
        max_vitals = cls.calculate_max_vitals(attributes)
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
    def calculate_max_vitals(cls, attributes: CharacterSessionAttributesDTO) -> CharacterSessionVitalsDTO:
        strength = attributes.strength
        endurance = attributes.endurance
        mental = attributes.mental

        hp = cls._resource_max(endurance * 10.0 + strength * 2.0)
        energy = cls._resource_max(mental * 5.0 + endurance * 2.0)
        stamina = cls._resource_max(endurance * 10.0)

        return CharacterSessionVitalsDTO(
            hp=VitalValueDTO(cur=hp, max=hp, regen=round(endurance * 0.1, 4)),
            energy=VitalValueDTO(cur=energy, max=energy, regen=round(mental * 0.1, 4)),
            stamina=VitalValueDTO(cur=stamina, max=stamina, regen=round(endurance * 0.2, 4)),
        )

    @staticmethod
    def apply_regen(vitals: CharacterSessionVitalsDTO) -> CharacterSessionVitalsDTO:
        now = datetime.now(UTC).timestamp()
        if vitals.last_update <= 0:
            vitals.last_update = now
            return vitals

        elapsed = now - vitals.last_update
        if elapsed < 1.0:
            return vitals

        for attr_name in ("hp", "energy", "stamina"):
            value = getattr(vitals, attr_name)
            if value.cur < value.max and value.regen > 0:
                value.cur = min(value.max, int(value.cur + value.regen * elapsed))

        vitals.last_update = now
        return vitals

    @staticmethod
    def _merge_current(current: VitalValueDTO, calculated: VitalValueDTO, *, fill_current: bool) -> VitalValueDTO:
        current_value = calculated.max if fill_current else max(0, min(int(current.cur), calculated.max))
        return VitalValueDTO(cur=current_value, max=calculated.max, regen=calculated.regen)

    @staticmethod
    def _resource_max(value: float) -> int:
        return max(1, int(round(value)))

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
