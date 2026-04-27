from src.backend.resources.game_data.skills.schemas import SkillCategory, SkillDTO, SkillGroup

SOCIAL_SKILLS = [
    SkillDTO(
        skill_key="leadership",
        name_en="Leadership",
        name_ru="Лидерство",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        stat_weights={"charisma": 2, "men": 1, "wisdom": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Способность вести за собой людей и вдохновлять их.",
    ),
    SkillDTO(
        skill_key="organization",
        name_en="Organization",
        name_ru="Организация",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        stat_weights={"intelligence": 2, "charisma": 1, "wisdom": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Умение организовывать процессы и людей.",
    ),
    SkillDTO(
        skill_key="team_spirit",
        name_en="Team Spirit",
        name_ru="Командный дух",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        stat_weights={"charisma": 2, "men": 1, "luck": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Способность работать в команде и поддерживать моральный дух.",
    ),
    SkillDTO(
        skill_key="egoism",
        name_en="Egoism",
        name_ru="Эгоизм",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        stat_weights={"men": 2, "luck": 2},  # Dual 2+2
        rate_mod=1.0,
        wall_mod=1.0,
        description="Сосредоточенность на собственных интересах.",
    ),
]
