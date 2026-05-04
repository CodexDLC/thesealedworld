from collections import defaultdict

from loguru import logger as log

from src.backend.resources.game_data.skills.definitions.armor import ARMOR_SKILLS
from src.backend.resources.game_data.skills.definitions.combat_support import COMBAT_SUPPORT_SKILLS
from src.backend.resources.game_data.skills.definitions.crafting import CRAFTING_SKILLS
from src.backend.resources.game_data.skills.definitions.gathering import GATHERING_SKILLS
from src.backend.resources.game_data.skills.definitions.social import SOCIAL_SKILLS
from src.backend.resources.game_data.skills.definitions.survival import SURVIVAL_SKILLS
from src.backend.resources.game_data.skills.definitions.tactical import TACTICAL_SKILLS
from src.backend.resources.game_data.skills.definitions.trade import TRADE_SKILLS

# Импорт определений
from src.backend.resources.game_data.skills.definitions.weapon_mastery import WEAPON_MASTERY_SKILLS
from src.backend.resources.game_data.skills.schemas import SkillCategory, SkillDTO, SkillGroup

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

# 1. Основной реестр: Key -> DTO
SKILL_REGISTRY: dict[str, SkillDTO] = {}

# 2. Индекс по категориям: Category -> List[SkillDTO]
SKILLS_BY_CATEGORY: dict[SkillCategory, list[SkillDTO]] = defaultdict(list)

# 3. Индекс по группам: Group -> List[SkillDTO]
SKILLS_BY_GROUP: dict[SkillGroup, list[SkillDTO]] = defaultdict(list)

_INITIALIZED = False


def _register_skills(skill_list: list[SkillDTO]) -> None:
    """
    Регистрирует список навыков в глобальных реестрах.
    Строит индексы для быстрого поиска.
    """
    for skill in skill_list:
        # 1. Проверка дубликатов
        if skill.skill_key in SKILL_REGISTRY:
            log.warning(f"SkillLibrary | Duplicate skill key detected: '{skill.skill_key}'. Overwriting.")

        # 2. Основной реестр
        SKILL_REGISTRY[skill.skill_key] = skill

        # 3. Индексы
        SKILLS_BY_CATEGORY[skill.category].append(skill)
        SKILLS_BY_GROUP[skill.group].append(skill)


def _initialize_library() -> None:
    """
    Инициализирует библиотеку навыков, загружая все определения.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return

    log.info("SkillLibrary | Initializing Skill Library 2.0...")

    all_skills_groups = [
        WEAPON_MASTERY_SKILLS,
        TACTICAL_SKILLS,
        ARMOR_SKILLS,
        COMBAT_SUPPORT_SKILLS,
        CRAFTING_SKILLS,
        GATHERING_SKILLS,
        TRADE_SKILLS,
        SOCIAL_SKILLS,
        SURVIVAL_SKILLS,
    ]

    count = 0
    for group in all_skills_groups:
        _register_skills(group)
        count += len(group)

    log.info(f"SkillLibrary | Initialization complete. Loaded {count} skills.")
    _INITIALIZED = True


# ==========================================
# PUBLIC API
# ==========================================


def get_skill_config(skill_key: str) -> SkillDTO | None:
    """
    Возвращает конфигурацию навыка (DTO) по его ключу.
    O(1) доступ.
    """
    return SKILL_REGISTRY.get(skill_key)


def get_all_skills() -> list[SkillDTO]:
    """
    Возвращает список всех зарегистрированных навыков.
    """
    return list(SKILL_REGISTRY.values())


def get_skills_by_category(category: SkillCategory) -> list[SkillDTO]:
    """
    Возвращает все навыки определенной категории (например, COMBAT).
    """
    return SKILLS_BY_CATEGORY.get(category, [])


def get_skills_by_group(group: SkillGroup) -> list[SkillDTO]:
    """
    Возвращает все навыки определенной группы (например, WEAPON_MASTERY).
    """
    return SKILLS_BY_GROUP.get(group, [])


# Автоматическая инициализация при импорте модуля
_initialize_library()
