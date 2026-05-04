from collections import defaultdict

from src.backend.features.game_catalog.skills.dto import SkillCategory, SkillDefinitionDTO, SkillGroup
from src.backend.features.game_catalog.skills.resources.definitions.armor import ARMOR_SKILLS
from src.backend.features.game_catalog.skills.resources.definitions.combat_support import COMBAT_SUPPORT_SKILLS
from src.backend.features.game_catalog.skills.resources.definitions.crafting import CRAFTING_SKILLS
from src.backend.features.game_catalog.skills.resources.definitions.gathering import GATHERING_SKILLS
from src.backend.features.game_catalog.skills.resources.definitions.social import SOCIAL_SKILLS
from src.backend.features.game_catalog.skills.resources.definitions.survival import SURVIVAL_SKILLS
from src.backend.features.game_catalog.skills.resources.definitions.tactical import TACTICAL_SKILLS
from src.backend.features.game_catalog.skills.resources.definitions.trade import TRADE_SKILLS
from src.backend.features.game_catalog.skills.resources.definitions.weapon_mastery import WEAPON_MASTERY_SKILLS

SKILL_GROUPS: tuple[list[SkillDefinitionDTO], ...] = (
    WEAPON_MASTERY_SKILLS,
    TACTICAL_SKILLS,
    ARMOR_SKILLS,
    COMBAT_SUPPORT_SKILLS,
    CRAFTING_SKILLS,
    GATHERING_SKILLS,
    TRADE_SKILLS,
    SOCIAL_SKILLS,
    SURVIVAL_SKILLS,
)


def load_skill_definitions() -> list[SkillDefinitionDTO]:
    registry: dict[str, SkillDefinitionDTO] = {}
    for group in SKILL_GROUPS:
        for skill in group:
            registry[skill.skill_key] = SkillDefinitionDTO.model_validate(skill)
    return list(registry.values())


def build_indexes(
    skills: list[SkillDefinitionDTO],
) -> tuple[dict[SkillCategory, list[SkillDefinitionDTO]], dict[SkillGroup, list[SkillDefinitionDTO]]]:
    by_category: dict[SkillCategory, list[SkillDefinitionDTO]] = defaultdict(list)
    by_group: dict[SkillGroup, list[SkillDefinitionDTO]] = defaultdict(list)
    for skill in skills:
        by_category[skill.category].append(skill)
        by_group[skill.group].append(skill)
    return dict(by_category), dict(by_group)
