from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

CRAFTING_SKILLS = [
    SkillDTO(
        skill_key="skill_alchemy",
        name_en="Alchemy",
        name_ru="Алхимия",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.CRAFTING,
        ui_group=SkillUiGroup.CRAFTING,
        stat_weights={"intellect": 2, "memory": 1, "prediction": 1},
        rate_mod=1.5,
        wall_mod=1.0,
        description=(
            "Работа с травами, реагентами, ядами, маслами и трансмутацией веществ.\n\n"
            "Даёт: качество зелий и ядов, силу алхимических эффектов и доступ к более сложным рецептам. "
            "Ограничение: требует подходящих реагентов и инструментов."
        ),
    ),
    SkillDTO(
        skill_key="skill_weapon_craft",
        name_en="Weapon Crafting",
        name_ru="Оружейное дело",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.CRAFTING,
        ui_group=SkillUiGroup.CRAFTING,
        stat_weights={"strength": 2, "agility": 1, "perception": 1},
        rate_mod=2.0,
        wall_mod=1.0,
        description=(
            "Производство, ремонт и улучшение оружия ближнего и дальнего боя.\n\n"
            "Даёт: качество оружия, шанс аффиксов и стабильность результата крафта. Ограничение: "
            "зависит от материалов, схем и доступного рабочего места."
        ),
    ),
    SkillDTO(
        skill_key="skill_armor_craft",
        name_en="Armor Crafting",
        name_ru="Бронное дело",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.CRAFTING,
        ui_group=SkillUiGroup.CRAFTING,
        stat_weights={"strength": 2, "endurance": 2},
        rate_mod=2.0,
        wall_mod=1.0,
        description=(
            "Производство и ремонт брони из металла, кожи, ткани и смешанных материалов.\n\n"
            "Даёт: базовую защиту, прочность и шанс защитных аффиксов на броне. Ограничение: тяжелые "
            "изделия сильнее зависят от качества материалов."
        ),
    ),
    SkillDTO(
        skill_key="skill_jewelry_craft",
        name_en="Jewelry Crafting",
        name_ru="Ювелирное дело",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.CRAFTING,
        ui_group=SkillUiGroup.CRAFTING,
        stat_weights={"agility": 2, "perception": 1, "prediction": 1},
        rate_mod=2.0,
        wall_mod=1.0,
        description=(
            "Тонкая работа с кольцами, амулетами, самоцветами и инкрустацией.\n\n"
            "Даёт: точность огранки, качество бонусов аксессуаров и шанс успешной инкрустации без "
            "потери камня."
        ),
    ),
    SkillDTO(
        skill_key="skill_artifact_craft",
        name_en="Artifact Crafting",
        name_ru="Создание артефактов",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.CRAFTING,
        ui_group=SkillUiGroup.CRAFTING,
        stat_weights={"mental": 2, "intellect": 1, "memory": 1},
        rate_mod=2.5,
        wall_mod=1.5,
        description=(
            "Создание артефактов, зачарованных предметов и нестабильных предметов силы.\n\n"
            "Даёт: силу магического эффекта, стабильность артефакта и доступ к высокоуровневым "
            "рецептам. Ограничение: сложнее качается и сильнее упирается в стену мастерства."
        ),
    ),
    SkillDTO(
        skill_key="skill_engineering",
        name_en="Engineering",
        name_ru="Инженерия",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.CRAFTING,
        ui_group=SkillUiGroup.CRAFTING,
        stat_weights={"intellect": 2, "agility": 1, "perception": 1},
        rate_mod=2.0,
        wall_mod=1.0,
        description=(
            "Проектирование механизмов, инструментов, ловушек и технических устройств.\n\n"
            "Даёт: сложность доступных устройств, надежность срабатывания ловушек и качество "
            "инженерных компонентов."
        ),
    ),
]
