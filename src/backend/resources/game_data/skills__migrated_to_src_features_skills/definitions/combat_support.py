from src.backend.resources.game_data.skills.schemas import SkillCategory, SkillDTO, SkillGroup

COMBAT_SUPPORT_SKILLS = [
    SkillDTO(
        skill_key="skill_parrying",
        name_en="Parrying",
        name_ru="Парирование",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT_SUPPORT,
        stat_weights={"agility": 2, "perception": 1, "strength": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Умение отражать удары противника оружием.",
    ),
    SkillDTO(
        skill_key="skill_anatomy",
        name_en="Anatomy",
        name_ru="Анатомия",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT_SUPPORT,
        stat_weights={"intelligence": 2, "perception": 2},  # Dual 2+2
        rate_mod=1.0,
        wall_mod=1.0,
        description="Знание анатомии для нанесения более эффективных ударов и лечения.",
    ),
    SkillDTO(
        skill_key="skill_tactics",
        name_en="Tactics",
        name_ru="Тактика",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT_SUPPORT,
        stat_weights={"intelligence": 2, "memory": 2},  # Dual 2+2 (Int + Mem)
        rate_mod=1.0,
        wall_mod=1.0,
        description="Зависит от Интеллекта и Памяти. Определяет сложность применяемых тактик.",
    ),
    SkillDTO(
        skill_key="skill_first_aid",
        name_en="First Aid",
        name_ru="Первая помощь",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT_SUPPORT,
        stat_weights={"memory": 2, "intelligence": 1, "agility": 1},  # Wis -> Memory
        rate_mod=1.0,
        wall_mod=1.0,
        description="Оказание первой помощи в полевых условиях.",
    ),
]
