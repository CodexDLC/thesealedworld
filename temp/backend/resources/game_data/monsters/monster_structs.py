from typing import Literal, NotRequired, TypedDict


# ==========================================
# 1. ХАРАКТЕРИСТИКИ (STATS)
# ==========================================
class MonsterStats(TypedDict):
    strength: int
    agility: int
    endurance: int
    intelligence: int
    wisdom: int
    men: int
    perception: int
    charisma: int
    luck: int


# ==========================================
# 2. ЭКИПИРОВКА (LOADOUT)
# ==========================================
class MonsterLoadout(TypedDict, total=False):
    main_hand: str | None
    off_hand: str | None
    head_armor: str | None
    chest_armor: str | None
    arms_armor: str | None
    legs_armor: str | None
    feet_armor: str | None
    chest_garment: str | None
    legs_garment: str | None
    outer_garment: str | None
    gloves_garment: str | None
    amulet: str | None
    ring_1: str | None
    ring_2: str | None
    belt_accessory: str | None


# ==========================================
# 3. СТРУКТУРА ВАРИАНТА (ЮНИТ)
# ==========================================
class MonsterVariant(TypedDict):
    id: str
    name_ru: NotRequired[str]  # Имя для отображения в UI
    role: Literal["minion", "veteran", "elite", "boss"]
    narrative_hint: str  # Описание для LLM
    cost: int  # "Цена" для балансировщика

    # Описания для UI
    description: NotRequired[str]  # Художественное описание (Бестиарий)
    combat_intro_text: NotRequired[str]  # Текст при появлении в бою

    # Свойства самого монстра (Traits).
    # Используем для боя (уязв. к яду) и LLM (описание).
    # НЕ ИСПОЛЬЗУЕМ для спавна (за это отвечает spawn_config).
    extra_tags: NotRequired[list[str]]

    min_tier: NotRequired[int]
    max_tier: NotRequired[int]

    base_stats: MonsterStats
    fixed_loadout: MonsterLoadout
    skills: list[str]

    # Служебные поля (проставляются в __init__ реестра)
    _family_ref: NotRequired[str]
    _archetype: NotRequired[str]


# ==========================================
# 4. СТРУКТУРА СЕМЬИ
# ==========================================
class FamilyHierarchy(TypedDict):
    minions: list[str]
    veterans: NotRequired[list[str]]  # Не у всех семей есть ветераны
    elites: list[str]
    boss: list[str]


class MonsterFamily(TypedDict):
    id: str
    archetype: Literal["humanoid", "beast", "undead", "construct", "demon", "unknown"]
    organization_type: Literal["solitary", "pack", "gang", "clan", "legion", "horde", "swarm"]

    # Общие теги семьи (просто как справочник свойств, например ["insect", "hive_mind"])
    # А НЕ ГЕОГРАФИЯ. География только в spawn_config.
    default_tags: list[str]

    hierarchy: FamilyHierarchy
    variants: dict[str, MonsterVariant]
