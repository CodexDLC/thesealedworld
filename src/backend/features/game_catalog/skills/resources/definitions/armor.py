from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

ARMOR_SKILLS = [
    SkillDTO(
        skill_key="skill_light_armor",
        name_en="Light Armor",
        name_ru="Легкая броня",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.ARMOR,
        stat_weights={"agility": 2, "endurance": 1, "perception": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Мобильная защитная школа для легкой брони, где основная защита — не принять удар вообще.\n\n"
            "Даёт: повышает кап уклонения от легкой брони и усиливает шанс контратаки после успешного "
            "уворота. Ограничение: если удар все же прошел, плоское поглощение ниже, чем у тяжелой брони."
        ),
    ),
    SkillDTO(
        skill_key="skill_medium_armor",
        name_en="Medium Armor",
        name_ru="Средняя броня",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.ARMOR,
        stat_weights={"endurance": 1, "strength": 1, "agility": 1, "perception": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Баланс защиты и подвижности: средняя броня переживает ошибки, не ломая темп боя полностью.\n\n"
            "Даёт: частично возвращает сниженный кап уклонения средней брони и поддерживает контратаку "
            "после успешного парирования. Ограничение: мобильность ниже, чем у легкой брони."
        ),
    ),
    SkillDTO(
        skill_key="skill_heavy_armor",
        name_en="Heavy Armor",
        name_ru="Тяжелая броня",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.ARMOR,
        stat_weights={"endurance": 2, "strength": 1, "mental": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Тяжелая броня для танкования, плоского снижения урона и контроля последствий попадания.\n\n"
            "Даёт: снижает эффективность критических и повторных попаданий, усиливает выживание под "
            "броней. Штраф: жестко режет кап уклонения грудной броней тяжелого класса."
        ),
    ),
]
