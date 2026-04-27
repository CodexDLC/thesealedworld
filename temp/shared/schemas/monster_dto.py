"""
Модуль содержит DTO для валидации конфигурации монстров.
Превращает статические словари (Config) в типизированные объекты (Runtime).
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- 1. ENUMS (Чтобы не писать строки руками) ---
MonsterRole = Literal["minion", "veteran", "elite", "boss"]
MonsterArchetype = Literal["humanoid", "beast", "undead", "construct", "demon", "unknown"]
OrganizationType = Literal["solitary", "pack", "gang", "clan", "legion", "horde", "swarm"]


# --- 2. КОМПОНЕНТЫ ---
class MonsterStatsDTO(BaseModel):
    """Характеристики монстра."""

    strength: int = Field(ge=0)
    agility: int = Field(ge=0)
    endurance: int = Field(ge=0)
    intelligence: int = Field(ge=0)
    wisdom: int = Field(ge=0)
    men: int = Field(ge=0)
    perception: int = Field(ge=0)
    charisma: int = Field(ge=0)
    luck: int


class MonsterLoadoutDTO(BaseModel):
    """Экипировка монстра."""

    main_hand: str | None = None
    off_hand: str | None = None
    head_armor: str | None = None
    chest_armor: str | None = None
    arms_armor: str | None = None
    legs_armor: str | None = None
    feet_armor: str | None = None
    chest_garment: str | None = None
    legs_garment: str | None = None
    outer_garment: str | None = None
    gloves_garment: str | None = None
    amulet: str | None = None
    ring_1: str | None = None
    ring_2: str | None = None
    belt_accessory: str | None = None


# --- 3. ВАРИАНТ МОНСТРА (ЮНИТ) ---
class MonsterVariantDTO(BaseModel):
    """Вариант монстра (шаблон)."""

    id: str
    role: MonsterRole
    narrative_hint: str
    cost: int = Field(gt=0, description="Цена юнита для балансировщика")

    # Авто-фикс: если в конфиге нет поля, будет пустой список
    extra_tags: list[str] = Field(default_factory=list)

    min_tier: int = Field(ge=0, le=11)
    max_tier: int = Field(ge=0, le=11)

    base_stats: MonsterStatsDTO
    # Авто-фикс: если нет лодаута, будет пустой объект
    fixed_loadout: MonsterLoadoutDTO = Field(default_factory=MonsterLoadoutDTO)

    # Авто-фикс: если ключа нет в словаре -> будет пустой список
    skills: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_tiers(self):
        if self.min_tier > self.max_tier:
            raise ValueError(f"Unit {self.id}: min_tier ({self.min_tier}) > max_tier ({self.max_tier})")
        return self


# --- 4. СЕМЬЯ ---
class FamilyHierarchyDTO(BaseModel):
    """Иерархия семьи монстров."""

    minions: list[str] = Field(default_factory=list)
    veterans: list[str] = Field(default_factory=list)
    elites: list[str] = Field(default_factory=list)
    boss: list[str] = Field(default_factory=list)


class MonsterFamilyDTO(BaseModel):
    """Семья монстров."""

    id: str
    archetype: MonsterArchetype
    organization_type: OrganizationType
    default_tags: list[str] = Field(default_factory=list)
    hierarchy: FamilyHierarchyDTO

    # Главная магия: Pydantic пройдет по словарю variant'ов и каждый превратит в DTO
    variants: dict[str, MonsterVariantDTO]

    @model_validator(mode="after")
    def validate_hierarchy_integrity(self):
        """Проверяет, что все ID из иерархии реально существуют в variants"""
        all_variant_ids = set(self.variants.keys())

        # Собираем все ID из иерархии
        hierarchy_ids = set()
        hierarchy_ids.update(self.hierarchy.minions)
        hierarchy_ids.update(self.hierarchy.veterans)
        hierarchy_ids.update(self.hierarchy.elites)
        hierarchy_ids.update(self.hierarchy.boss)

        # Проверяем, нет ли в иерархии "мертвых душ"
        missing = hierarchy_ids - all_variant_ids
        if missing:
            raise ValueError(f"Family {self.id}: Hierarchy references missing variants: {missing}")

        return self


class GeneratedMonsterDTO(BaseModel):
    """
    DTO для использования монстра в ИГРЕ (Бой, Диалоги).
    Превращает JSON-поля из БД в удобные объекты.
    """

    id: UUID  # Вернул UUID
    family_id: UUID | str  # В БД это UUID, но может быть строкой в DTO
    variant_id: str
    name: str
    description: str | dict | None  # В БД это JSON (dict), но может быть строкой

    level: int
    cost: int
    role: str

    # В БД это JSON, а здесь это строгие типы!
    attributes: MonsterStatsDTO
    loadout: MonsterLoadoutDTO
    skills: list[str]
    tags: list[str] | None = None

    # Если монстр ранен, тут будет состояние, иначе None
    current_state: dict | None = None

    model_config = ConfigDict(from_attributes=True)
