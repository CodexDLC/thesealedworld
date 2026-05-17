from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

SOCIAL_SKILLS = [
    SkillDTO(
        skill_key="skill_leadership",
        name_en="Leadership",
        name_ru="Лидерство",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        ui_group=SkillUiGroup.LEADERSHIP,
        stat_weights={"projection": 2, "mental": 1, "memory": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Авторитет и прямое командование людьми, группами и боевыми единицами.\n\n"
            "Даёт: больший лимит управляемых союзников и масштаб командования от пары до рейдовой "
            "структуры. Ограничение: требует реальных союзников или подчиненных."
        ),
    ),
    SkillDTO(
        skill_key="skill_organization",
        name_en="Organization",
        name_ru="Организация",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        ui_group=SkillUiGroup.LEADERSHIP,
        stat_weights={"intellect": 2, "projection": 1, "memory": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Структура, права доступа и управление организациями, кланами и владениями.\n\n"
            "Даёт: право создавать и расширять организационные структуры, открывает управление "
            "кланом, альянсом и владениями по мере мастерства."
        ),
    ),
    SkillDTO(
        skill_key="skill_team_spirit",
        name_en="Team Spirit",
        name_ru="Командный дух",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        ui_group=SkillUiGroup.LEADERSHIP,
        stat_weights={"projection": 2, "mental": 1, "prediction": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Командная синергия, мораль и полезность персонажа для группы самим присутствием.\n\n"
            "Даёт: групповые баффы, ауры и усиление союзников. Ограничение: раскрывается рядом с "
            "командой, а не в одиночку."
        ),
    ),
    SkillDTO(
        skill_key="skill_egoism",
        name_en="Egoism",
        name_ru="Эгоизм",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.SOCIAL,
        ui_group=SkillUiGroup.LEADERSHIP,
        stat_weights={"mental": 2, "prediction": 2},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Протокол одиночки: эффективность персонажа, когда рядом нет союзников.\n\n"
            "Даёт: персональные баффы к урону, восстановлению или выживанию в solo-режиме. "
            "Ограничение: бонусы отключаются или слабеют при появлении союзников рядом."
        ),
    ),
]
