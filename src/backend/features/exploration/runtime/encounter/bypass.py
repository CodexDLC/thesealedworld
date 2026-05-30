from __future__ import annotations

from typing import Any

from src.backend.features.exploration.integrations.encounter_integration import ENCOUNTER_SKILL_KEYS
from src.shared.schemas.exploration import EncounterDTO, EncounterOptionDTO

BYPASS_SKILL_KEYS = ("skill_scouting", "skill_hunting")


def calculate_bypass_chance(skills: Any, base_bypass_chance: float = 0.14) -> float:
    """Return a 0..1 bypass chance from exploration encounter skills."""
    values = [_normalized_skill(_skill_value(skills, skill_key)) for skill_key in BYPASS_SKILL_KEYS]
    skill_factor = sum(values) / len(values) if values else 0.0
    return min(1.0, base_bypass_chance + skill_factor * (1.0 - base_bypass_chance))


def bypass_chance_percent(chance: float) -> int:
    return max(0, min(100, round(float(chance) * 100)))


def encounter_with_bypass_chance(
    encounter: EncounterDTO,
    chance: float,
    *,
    result: dict[str, Any] | None = None,
) -> EncounterDTO:
    percent = bypass_chance_percent(chance)
    metadata = dict(encounter.metadata or {})
    metadata["bypass_chance"] = float(chance)
    metadata["bypass_chance_percent"] = percent
    if result is not None:
        metadata["bypass_result"] = dict(result)
    return encounter.model_copy(
        update={
            "metadata": metadata,
            "options": _ensure_bypass_options(encounter.options, chance),
        }
    )


def _ensure_bypass_options(options: list[EncounterOptionDTO], chance: float) -> list[EncounterOptionDTO]:
    percent = bypass_chance_percent(chance)
    clean_options = [option for option in options if option.id != "inspect"]

    has_attack = any(option.id == "attack" for option in clean_options)
    has_bypass = any(option.id == "bypass" for option in clean_options)

    if not has_attack:
        clean_options.insert(0, EncounterOptionDTO(id="attack", label="В бой!", style="danger"))

    if not has_bypass:
        insert_at = 1 if clean_options and clean_options[0].id == "attack" else len(clean_options)
        clean_options.insert(insert_at, EncounterOptionDTO(id="bypass", label="Обойти", style="secondary"))

    hydrated: list[EncounterOptionDTO] = []
    for option in clean_options:
        if option.id == "bypass":
            hydrated.append(
                option.model_copy(
                    update={
                        "label": option.label or "Обойти",
                        "style": option.style or "secondary",
                        "chance": float(chance),
                        "chance_percent": percent,
                    }
                )
            )
        else:
            hydrated.append(option)
    return hydrated


def _skill_value(skills: Any, skill_key: str) -> Any:
    if skill_key not in ENCOUNTER_SKILL_KEYS:
        return 0.0
    if hasattr(skills, "value"):
        return skills.value(skill_key)
    if isinstance(skills, dict):
        return skills.get(skill_key, 0.0)
    return getattr(skills, skill_key, 0.0)


def _normalized_skill(raw: Any) -> float:
    if isinstance(raw, dict):
        if raw.get("unlocked") is False:
            return 0.0
        raw = raw.get("value", raw.get("xp", raw.get("total_xp", raw.get("level", 0.0))))
    try:
        value = max(0.0, float(raw or 0.0))
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, value / 100.0 if value > 1.0 else value)
