from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup

SURVIVAL_SKILLS = [
    SkillDTO(
        skill_key="taming",
        name_en="Taming",
        name_ru="Приручение",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SURVIVAL,
        stat_weights={"projection": 2, "memory": 1, "mental": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Способность приручать диких животных и управлять ими.",
    ),
    SkillDTO(
        skill_key="adaptation",
        name_en="Adaptation",
        name_ru="Адаптация",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SURVIVAL,
        stat_weights={"endurance": 2, "mental": 2},  # Dual 2+2
        rate_mod=1.0,
        wall_mod=1.0,
        description="Умение выживать в агрессивной среде, сопротивляться погодным условиям и болезням.",
    ),
    SkillDTO(
        skill_key="scouting",
        name_en="Scouting",
        name_ru="Выслеживание",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SURVIVAL,
        stat_weights={"perception": 2, "memory": 1, "agility": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Умение находить безопасные пути, избегать нежелательных встреч и выслеживать цели.",
    ),
]
