from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

TACTICAL_SKILLS = [
    SkillDTO(
        skill_key="skill_one_handed",
        name_en="One Handed Style",
        name_ru="Одноручный стиль",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.TACTICAL,
        stat_weights={"agility": 2, "perception": 1, "strength": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Стиль одной руки: оружие в основной руке, вторая рука свободна или не задает отдельный стиль.\n\n"
            "Даёт: стабильный базовый темп без врожденного штрафа стиля; стильный триггер Flow может "
            "сохранять тактические токены при использовании финтов."
        ),
    ),
    SkillDTO(
        skill_key="skill_two_handed",
        name_en="Two Handed Style",
        name_ru="Двуручный стиль",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.TACTICAL,
        stat_weights={"strength": 2, "endurance": 1, "agility": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Стиль тяжелого хвата двумя руками для оружия с большой инерцией и сильным пробитием.\n\n"
            "Даёт: доступ к стилю Ignore, который помогает обходить броню и ослаблять активную защиту. "
            "Мастерство снижает штраф двуручного оружия к уклонению."
        ),
    ),
    SkillDTO(
        skill_key="skill_shield_mastery",
        name_en="Shield Mastery",
        name_ru="Владение щитом",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.TACTICAL,
        stat_weights={"strength": 2, "endurance": 1, "agility": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Стиль боя со щитом: защита, поглощение удара и ответ через щитовые приемы.\n\n"
            "Даёт: усиливает поглощение и отражение урона щитом, помогает снижать штрафы щита к "
            "уклонению. Сам шанс блока сейчас умножается навыком Парирование."
        ),
    ),
    SkillDTO(
        skill_key="skill_dual_wield",
        name_en="Dual Wield",
        name_ru="Бой двумя руками",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.TACTICAL,
        stat_weights={"agility": 2, "perception": 1, "strength": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Стиль двух оружий: основная атака дополняется ударом второй рукой.\n\n"
            "Даёт: шанс дополнительной атаки off-hand, повышает качество урона второй руки и помогает "
            "перекрывать штраф точности оружия во второй руке."
        ),
    ),
]
