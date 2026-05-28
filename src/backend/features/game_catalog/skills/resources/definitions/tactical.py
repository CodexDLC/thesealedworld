from src.backend.features.game_catalog.skills.dto.catalog import SkillCategory, SkillDTO, SkillGroup, SkillUiGroup

TACTICAL_SKILLS = [
    SkillDTO(
        skill_key="skill_ranged_combat",
        name_en="Ranged Combat",
        name_ru="Дальний бой",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.TACTICAL,
        stat_weights={"agility": 1, "memory": 1, "perception": 1, "prediction": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Тактика стрелка в размене: уход с линии, сохранение дистанции и работа против ответных атак.\n\n"
            "Даёт: триггер Идеальный отскок с шансом до 25% может превратить входящую атаку в гарантированный "
            "уворот. Стрелковые тактические финты выдаются отдельно и не открываются в тяжелой броне."
        ),
    ),
    SkillDTO(
        skill_key="skill_two_handed",
        name_en="Two Handed Style",
        name_ru="Двуручный стиль",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.TACTICAL,
        stat_weights={"strength": 2, "endurance": 1, "perception": 1},
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
        stat_weights={"endurance": 1, "strength": 1, "mental": 1, "memory": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Стиль боя со щитом: щит используется как off-hand инструмент для частичного поглощения удара "
            "и ответного урона.\n\n"
            "Даёт: триггер Kinetic Reflection при провале блока может погасить часть прошедшего удара. "
            "Мастерство задает лимит поглощения: до 50% входящего урона на 100 мастерства. Возврат тоже "
            "масштабируется мастерством: до 50% от поглощенной части на 100 мастерства. Это не полный блок "
            "и не парирование в 0 урона; сам шанс блока сейчас умножается навыком Парирование."
        ),
    ),
    SkillDTO(
        skill_key="skill_dual_wield",
        name_en="Dual Wield",
        name_ru="Бой двумя руками",
        category=SkillCategory.COMBAT,
        group=SkillGroup.COMBAT,
        ui_group=SkillUiGroup.TACTICAL,
        stat_weights={"agility": 1, "perception": 1, "prediction": 1, "memory": 1},
        rate_mod=1.0,
        wall_mod=1.0,
        description=(
            "Стиль двух оружий: основная атака дополняется ударом второй рукой.\n\n"
            "Даёт: шанс дополнительной атаки off-hand после успешной проверки точности основной руки. "
            "Базовый шанс 25%, мастерство поднимает его до 50% на 100 мастерства. Дополнительная атака "
            "второй рукой сама не может запускать еще одну такую же цепочку."
        ),
    ),
]
