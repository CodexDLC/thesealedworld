from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

SURVIVAL_SKILLS = [
    SkillDTO(
        skill_key="skill_taming",
        name_en="Taming",
        name_ru="Приручение",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.SURVIVAL,
        stat_weights={"projection": 2, "memory": 1, "mental": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Нейросинхронизация и контроль диких существ, превращающих зверя в управляемого спутника.\n\n"
            "Даёт: силу и надежность питомцев через общий множитель характеристик, а также доступ к "
            "более сложному приручению. Ограничение: требует подходящую цель и условия контакта."
        ),
    ),
    SkillDTO(
        skill_key="skill_adaptation",
        name_en="Adaptation",
        name_ru="Адаптация",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.SURVIVAL,
        stat_weights={"endurance": 2, "mental": 1, "memory": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Перестройка тела и симбиота под агрессивную среду, болезни, яд и контроль.\n\n"
            "Даёт: общий множитель сопротивлений к физическим, магическим, биологическим и контрольным "
            "угрозам. Ограничение: не заменяет броню, а усиливает базовые сопротивления."
        ),
    ),
    SkillDTO(
        skill_key="skill_scouting",
        name_en="Scouting",
        name_ru="Выслеживание",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.SURVIVAL,
        stat_weights={"perception": 2, "memory": 1, "prediction": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Разведка живых угроз: следы, признаки засады, состав энкаунтера и возможность выбора до боя.\n\n"
            "Даёт: контроль столкновений, информацию о враге, обход опасностей и на высоком мастерстве "
            "предпросмотр ценного лута."
        ),
    ),
    SkillDTO(
        skill_key="skill_pathfinder",
        name_en="Pathfinder",
        name_ru="Навигация",
        category=SkillCategory.NON_COMBAT,
        group=SkillGroup.WORLD,
        ui_group=SkillUiGroup.SURVIVAL,
        stat_weights={"perception": 2, "endurance": 1, "memory": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Чтение ландшафта, маршрутов, ловушек и скрытых проходов между локациями.\n\n"
            "Даёт: обнаружение ловушек, сокращение времени пути и доступ к скрытым маршрутам. "
            "Ограничение: работает по среде, а не по живым врагам."
        ),
    ),
]
