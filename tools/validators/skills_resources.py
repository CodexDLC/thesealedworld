from __future__ import annotations

from typing import TYPE_CHECKING

from src.backend.features.character.resources import CHARACTER_ATTRIBUTE_TEXT
from src.backend.features.game_catalog.skills.services import SkillCatalogService

if TYPE_CHECKING:
    from pathlib import Path


def validate_skills_resources(root: Path) -> list[str]:
    _ = root
    errors: list[str] = []
    catalog = SkillCatalogService()

    valid_attributes = set(CHARACTER_ATTRIBUTE_TEXT)
    if not catalog.skills:
        errors.append("skills: catalog is empty")

    for skill in catalog.skills:
        if not skill.description:
            errors.append(f"skills:{skill.skill_key}: missing description")
        if not skill.name_ru:
            errors.append(f"skills:{skill.skill_key}: missing name_ru")
        for attr_key in skill.stat_weights:
            if attr_key not in valid_attributes:
                errors.append(f"skills:{skill.skill_key}: unknown stat weight: {attr_key}")

    return errors
