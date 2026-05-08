from enum import StrEnum

from pydantic import BaseModel, Field


class SkillCategory(StrEnum):
    COMBAT = "combat"
    NON_COMBAT = "non_combat"


class SkillGroup(StrEnum):
    COMBAT = "combat"
    WORLD = "world"
    CRAFTING = "crafting"
    SOCIAL = "social"


class SkillUiGroup(StrEnum):
    WEAPON_MASTERY = "weapon_mastery"
    TACTICAL = "tactical"
    ARMOR = "armor"
    COMBAT_SUPPORT = "combat_support"
    GATHERING = "gathering"
    SURVIVAL = "survival"
    CRAFTING = "crafting"
    TRADE = "trade"
    LEADERSHIP = "leadership"


class SkillDefinitionDTO(BaseModel):
    skill_key: str = Field(min_length=1)
    name_en: str = Field(min_length=1)
    name_ru: str = Field(min_length=1)
    category: SkillCategory = SkillCategory.NON_COMBAT
    group: SkillGroup = SkillGroup.WORLD
    ui_group: SkillUiGroup = SkillUiGroup.SURVIVAL
    stat_weights: dict[str, float] = Field(default_factory=dict)
    rate_mod: float = 1.0
    wall_mod: float = 1.0
    description: str | None = None

    def to_public_catalog_item(self) -> dict[str, object]:
        return {
            "title": self.name_ru,
            "title_en": self.name_en,
            "description": self.description or f"DATA_MISSING: skill_description:{self.skill_key}",
            "category": self.category.value,
            "group": self.group.value,
            "ui_group": self.ui_group.value,
            "ui_tags": ["skill", self.category.value, self.group.value, self.ui_group.value],
        }


SkillDTO = SkillDefinitionDTO
