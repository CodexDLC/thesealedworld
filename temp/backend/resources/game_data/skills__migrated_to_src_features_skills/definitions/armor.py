from src.backend.resources.game_data.skills.schemas import SkillCategory, SkillDTO, SkillGroup

ARMOR_SKILLS = [
    SkillDTO(
        skill_key="skill_light_armor",
        name_en="Light Armor",
        name_ru="Легкая броня",
        category=SkillCategory.COMBAT,
        group=SkillGroup.ARMOR,
        stat_weights={"agility": 2, "endurance": 1, "perception": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Ношение легкой брони, не сковывающей движения.",
    ),
    SkillDTO(
        skill_key="skill_medium_armor",
        name_en="Medium Armor",
        name_ru="Средняя броня",
        category=SkillCategory.COMBAT,
        group=SkillGroup.ARMOR,
        stat_weights={"endurance": 2, "strength": 1, "agility": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description="Ношение средней брони, баланс между защитой и подвижностью.",
    ),
    SkillDTO(
        skill_key="skill_heavy_armor",
        name_en="Heavy Armor",
        name_ru="Тяжелая броня",
        category=SkillCategory.COMBAT,
        group=SkillGroup.ARMOR,
        stat_weights={"strength": 2, "endurance": 2},  # Dual 2+2
        rate_mod=1.0,
        wall_mod=1.0,
        description="Ношение тяжелой брони, обеспечивающей максимальную защиту.",
    ),
]
