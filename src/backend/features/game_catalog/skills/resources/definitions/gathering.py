from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

GATHERING_SKILLS = [
    SkillDTO(
        skill_key="skill_mining",
        name_en="Mining",
        name_ru="Горное дело",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.GATHERING,
        stat_weights={"strength": 2, "endurance": 2},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Добыча руды, камня и самоцветов с помощью кирки и тяжелого труда.\n\n"
            "Даёт: количество и качество добычи, шанс редких жил и эффективность работы с камнем. "
            "Ограничение: требует подходящий инструмент и доступный ресурсный узел."
        ),
    ),
    SkillDTO(
        skill_key="skill_herbalism",
        name_en="Herbalism",
        name_ru="Травничество",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.GATHERING,
        stat_weights={"perception": 2, "memory": 1, "intellect": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Поиск и сбор трав, грибов, кореньев и природных реагентов.\n\n"
            "Даёт: шанс найти ценные растения, качество алхимического сырья и меньше потерь при "
            "сборе. Ограничение: зависит от биома и сезона ресурса."
        ),
    ),
    SkillDTO(
        skill_key="skill_skinning",
        name_en="Skinning",
        name_ru="Снятие шкур",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.GATHERING,
        stat_weights={"agility": 2, "perception": 1, "endurance": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Аккуратное разделывание туш, снятие шкур, меха, костей и других трофеев.\n\n"
            "Даёт: качество кожи и меха, шанс редких частей и меньше порчи добычи. Ограничение: "
            "нужен подходящий инструмент и подходящая цель."
        ),
    ),
    SkillDTO(
        skill_key="skill_woodcutting",
        name_en="Woodcutting",
        name_ru="Лесорубство",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.GATHERING,
        stat_weights={"strength": 2, "endurance": 2},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Заготовка древесины, бревен и угля через работу с деревьями и лесными узлами.\n\n"
            "Даёт: количество и качество древесины, шанс редких пород и эффективность рубки. "
            "Ограничение: требует топор или другой подходящий инструмент."
        ),
    ),
    SkillDTO(
        skill_key="skill_hunting",
        name_en="Hunting",
        name_ru="Охота",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.GATHERING,
        stat_weights={"perception": 2, "agility": 1, "endurance": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Поиск, преследование и добыча диких животных до этапа разделки.\n\n"
            "Даёт: шанс найти дичь, качество охотничьих трофеев и лучшее чтение следов. Ограничение: "
            "часть результата зависит от местности и поведения цели."
        ),
    ),
    SkillDTO(
        skill_key="skill_archaeology",
        name_en="Archaeology",
        name_ru="Археология",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.GATHERING,
        stat_weights={"perception": 2, "memory": 1, "intellect": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Раскопки, поиск древностей, схем, артефактов и следов погибших культур.\n\n"
            "Даёт: шанс найти скрытые находки, качество археологических ресурсов и доступ к более "
            "сложным раскопкам."
        ),
    ),
]
