from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

COMBAT_SUPPORT_SKILLS = [
    SkillDTO(
        skill_key="skill_parrying",
        name_en="Parrying",
        name_ru="Парирование",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.COMBAT_SUPPORT,
        stat_weights={"perception": 2, "prediction": 1, "agility": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Активная защита через оружие, баклер или щит: контроль углов, линии удара и момента ответа.\n\n"
            "Даёт: умножает базовый шанс парирования от оружия, баклера или другого предмета с parry-базой. "
            "Блок полноразмерным щитом масштабируется отдельным навыком Владение щитом. Ограничение: без "
            "предмета с parry-базой навык сам по себе защиту не создает."
        ),
    ),
    SkillDTO(
        skill_key="skill_anatomy",
        name_en="Anatomy",
        name_ru="Анатомия",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.COMBAT_SUPPORT,
        stat_weights={"intellect": 2, "perception": 1, "memory": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Понимание тела, ран и восстановления: как организм принимает урон и возвращает ресурс.\n\n"
            "Даёт: усиливает естественное восстановление и входящее лечение; в боевой прогрессии "
            "получает опыт от нанесенного и принятого урона."
        ),
    ),
    SkillDTO(
        skill_key="skill_tactics",
        name_en="Tactics",
        name_ru="Тактика",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.COMBAT_SUPPORT,
        stat_weights={"intellect": 2, "memory": 1, "prediction": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Чтение боевых паттернов: позиция, предсказание движения и выбор правильного момента.\n\n"
            "Даёт: поддерживает anti-evasion, уклонение и контратаку по дизайн-доку; в бою получает "
            "опыт за результативный размен и тактическое давление."
        ),
    ),
    SkillDTO(
        skill_key="skill_first_aid",
        name_en="First Aid",
        name_ru="Первая помощь",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.CRAFTING,
        ui_group=SkillUiGroup.CRAFTING,
        stat_weights={"memory": 2, "intellect": 1, "agility": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Полевая медицина и работа с расходниками восстановления вне прямого боевого мастерства.\n\n"
            "Даёт: качество лечебных предметов, силу лечения, сокращение задержки между перевязками "
            "и доступ к более сложным медицинским рецептам."
        ),
    ),
]
