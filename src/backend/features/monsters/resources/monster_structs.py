from typing import Literal, NotRequired, TypedDict


# ==========================================
# 1. ХАРАКТЕРИСТИКИ (STATS)
# ==========================================
class MonsterStats(TypedDict):
    strength: int
    agility: int
    endurance: int
    intellect: int
    memory: int
    mental: int
    perception: int
    projection: int
    prediction: int


# ==========================================
# 2. ЭКИПИРОВКА (LOADOUT)
# ==========================================
class MonsterLoadout(TypedDict, total=False):
    main_hand: str | None
    off_hand: str | None
    two_hand: str | None
    head_armor: str | None
    chest_armor: str | None
    arms_armor: str | None
    legs_armor: str | None
    feetwear: str | None
    chest_garment: str | None
    legs_garment: str | None
    outer_garment: str | None
    gloves_garment: str | None
    amulet: str | None
    ring_1: str | None
    ring_2: str | None
    belt_accessory: str | None


class MonsterSkillKit(TypedDict):
    base: dict[str, float]
    role_bonus: dict[str, dict[str, float]]


class MonsterLootProfile(TypedDict, total=False):
    salvage_type: str
    loot_mode: Literal["equipment", "salvage", "hybrid"]
    allowed_loadout_slots: Literal["full_humanoid", "natural_only", "none"]
    equipment_drop_policy: Literal["fixed_loadout", "curated", "none"]
    drops_as_equipment: bool
    materials: list[str]
    equipment_quality: str


class MonsterFamilyBalance(TypedDict, total=False):
    organization_divisor: float
    composition_profile: str
    max_elites_without_boss: int
    boss_allowed: bool


class MonsterEquipmentMapping(TypedDict, total=False):
    equipment_key: str
    source_base_id: str
    slots: list[str]
    tags: list[str]
    scaling_profile: str
    affix_pool: str


class MonsterClanResourceModel(TypedDict, total=False):
    tier_range: dict[str, int]
    balance: MonsterFamilyBalance
    text_hints: dict[str, object]
    ai_defaults: dict[str, object]
    item_mappings: dict[str, MonsterEquipmentMapping]
    allowed_affix_pools: list[str]


class MonsterMemberResourceModel(TypedDict, total=False):
    variant_key: str
    role: Literal["minion", "veteran", "elite", "boss"]
    tier_policy: Literal["role_offset", "fixed", "clan_tier"]
    member_tier_offset: int
    attribute_profile: dict[str, object]
    skill_profile: dict[str, object]
    item_loadout_profile: dict[str, object]
    ai_profile: dict[str, object]
    balance: dict[str, object]


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
    skill_overrides: NotRequired[dict[str, float | None]]
    member_model: NotRequired[MonsterMemberResourceModel]

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

    skill_kit: NotRequired[MonsterSkillKit]
    loot_profile: NotRequired[MonsterLootProfile]
    clan_model: NotRequired[MonsterClanResourceModel]
    member_models: NotRequired[list[MonsterMemberResourceModel]]

    hierarchy: FamilyHierarchy
    variants: dict[str, MonsterVariant]
