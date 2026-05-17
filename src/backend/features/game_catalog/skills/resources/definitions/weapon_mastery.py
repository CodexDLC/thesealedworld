from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

WEAPON_MASTERY_SKILLS = [
    SkillDTO(
        skill_key="skill_swords",
        name_en="Swordsmanship",
        name_ru="Владение мечами",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.WEAPON_MASTERY,
        stat_weights={"strength": 2, "agility": 1, "endurance": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Клинковая школа для мечей, палашей, катан и другого сбалансированного рубящего оружия.\n\n"
            "Даёт: лучше раскрывает точность и крит-триггеры мечей, снижает влияние штрафов оружия к "
            "точности и делает урон стабильнее за счет меньшего разброса."
        ),
    ),
    SkillDTO(
        skill_key="skill_fencing",
        name_en="Fencing",
        name_ru="Фехтование",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.WEAPON_MASTERY,
        stat_weights={"agility": 2, "perception": 1, "strength": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Техника короткого и колющего оружия: кинжалы, рапиры, стилеты, шпаги и похожие клинки.\n\n"
            "Даёт: повышает надежность точных уколов, раскрывает крит-триггеры фехтовального оружия "
            "и помогает перекрывать его штрафы к точности."
        ),
    ),
    SkillDTO(
        skill_key="skill_polearms",
        name_en="Polearms",
        name_ru="Древковое оружие",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.WEAPON_MASTERY,
        stat_weights={"strength": 2, "agility": 1, "perception": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Работа с копьями, алебардами, пиками, посохами и другим оружием дистанционного контроля.\n\n"
            "Даёт: лучше компенсирует штрафы древкового оружия к точности, стабилизирует урон и "
            "раскрывает триггеры контроля дистанции, пробития и сбивания движения."
        ),
    ),
    SkillDTO(
        skill_key="skill_macing",
        name_en="Mace Fighting",
        name_ru="Дробящее оружие",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.WEAPON_MASTERY,
        stat_weights={"strength": 2, "endurance": 1, "mental": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Владение булавами, молотами, топорами и другим тяжелым ударным оружием.\n\n"
            "Даёт: помогает перекрывать высокий штраф такого оружия к точности, стабилизирует урон и "
            "усиливает шанс крит-триггеров против брони, оглушения или тяжелого удара."
        ),
    ),
    SkillDTO(
        skill_key="skill_archery",
        name_en="Archery",
        name_ru="Стрельба из лука",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.WEAPON_MASTERY,
        stat_weights={"agility": 2, "perception": 1, "strength": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Дальнобойная школа для луков, арбалетов и другого оружия, где важны координация и глазомер.\n\n"
            "Даёт: лучше реализует точность выстрела, снижает влияние штрафов дальнобойного оружия и "
            "раскрывает позиционные или критические триггеры стрелкового оружия."
        ),
    ),
    SkillDTO(
        skill_key="skill_unarmed",
        name_en="Unarmed Combat",
        name_ru="Рукопашный бой",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.WEAPON_MASTERY,
        stat_weights={"agility": 2, "strength": 1, "endurance": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Бой телом, захватами и ударами без экипированного оружия.\n\n"
            "Даёт: превращает силу в урон эффективнее, снижает высокий разброс рукопашного удара и на "
            "высоком мастерстве открывает спецприемы контроля, мешающие цели уклоняться."
        ),
    ),
]
