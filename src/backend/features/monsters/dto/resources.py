from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

MonsterRole = Literal["minion", "veteran", "elite", "boss"]
MonsterArchetype = Literal["humanoid", "beast", "undead", "construct", "demon", "unknown"]
OrganizationType = Literal["solitary", "pack", "gang", "clan", "legion", "horde", "swarm"]
LootMode = Literal["equipment", "salvage", "hybrid"]
LootLoadoutSlots = Literal["full_humanoid", "natural_only", "none"]
EquipmentDropPolicy = Literal["fixed_loadout", "curated", "none"]
MemberTierPolicy = Literal["role_offset", "fixed", "clan_tier"]


class MonsterCombatProfileDTO(BaseModel):
    archetype: MonsterArchetype
    body_loadout: str | None = None
    armor_class: str | None = None
    natural_weapon_set: str | None = None
    equipment_scaling: str | None = None
    modifier_formula: str


class MonsterSkillKitDTO(BaseModel):
    base: dict[str, float] = Field(default_factory=dict)
    role_bonus: dict[MonsterRole, dict[str, float]] = Field(default_factory=dict)


class MonsterAbilityDefinitionDTO(BaseModel):
    mechanic: str
    presentation: str


class MonsterLootProfileDTO(BaseModel):
    salvage_type: str
    loot_mode: LootMode
    allowed_loadout_slots: LootLoadoutSlots
    equipment_drop_policy: EquipmentDropPolicy
    drops_as_equipment: bool
    materials: list[str] = Field(default_factory=list)
    equipment_quality: str | None = None


class MonsterStatsDTO(BaseModel):
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
    main_hand: str | None = None
    off_hand: str | None = None
    head_armor: str | None = None
    chest_armor: str | None = None
    arms_armor: str | None = None
    legs_armor: str | None = None
    feetwear: str | None = None
    chest_garment: str | None = None
    legs_garment: str | None = None
    outer_garment: str | None = None
    gloves_garment: str | None = None
    amulet: str | None = None
    ring_1: str | None = None
    ring_2: str | None = None
    belt_accessory: str | None = None


class MonsterTierRangeDTO(BaseModel):
    min_tier: int = Field(default=0, ge=0, le=11)
    max_tier: int = Field(default=11, ge=0, le=11)

    @model_validator(mode="after")
    def validate_tier_range(self) -> MonsterTierRangeDTO:
        if self.min_tier > self.max_tier:
            raise ValueError(f"Monster tier range min_tier ({self.min_tier}) > max_tier ({self.max_tier})")
        return self


class MonsterFamilyBalanceDTO(BaseModel):
    organization_divisor: float = Field(default=1.0, gt=0.0)
    composition_profile: str = "balanced"
    max_elites_without_boss: int = Field(default=1, ge=0)
    boss_allowed: bool = False


class MonsterEquipmentMappingDTO(BaseModel):
    """Family-level semantic key that will later resolve into generated items."""

    equipment_key: str
    source_base_id: str
    slots: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    scaling_profile: str | None = None
    affix_pool: str | None = None


class MonsterClanResourceModelDTO(BaseModel):
    tier_range: MonsterTierRangeDTO = Field(default_factory=MonsterTierRangeDTO)
    balance: MonsterFamilyBalanceDTO = Field(default_factory=MonsterFamilyBalanceDTO)
    text_hints: dict[str, Any] = Field(default_factory=dict)
    ai_defaults: dict[str, Any] = Field(default_factory=dict)
    item_mappings: dict[str, MonsterEquipmentMappingDTO] = Field(default_factory=dict)
    allowed_affix_pools: list[str] = Field(default_factory=list)


class MonsterMemberResourceModelDTO(BaseModel):
    variant_key: str
    role: MonsterRole
    tier_policy: MemberTierPolicy = "role_offset"
    member_tier_offset: int = 0
    attribute_profile: dict[str, Any] = Field(default_factory=dict)
    skill_profile: dict[str, Any] = Field(default_factory=dict)
    item_loadout_profile: dict[str, Any] = Field(default_factory=dict)
    ability_profile: dict[str, Any] = Field(default_factory=dict)
    ai_profile: dict[str, Any] = Field(default_factory=dict)
    balance: dict[str, Any] = Field(default_factory=dict)


class MonsterVariantDTO(BaseModel):
    id: str
    role: MonsterRole
    narrative_hint: str
    cost: int = Field(gt=0)
    extra_tags: list[str] = Field(default_factory=list)
    min_tier: int = Field(default=0, ge=0, le=11)
    max_tier: int = Field(default=11, ge=0, le=11)
    base_stats: MonsterStatsDTO
    fixed_loadout: MonsterLoadoutDTO = Field(default_factory=MonsterLoadoutDTO)
    skills: list[str] = Field(default_factory=list)
    skill_overrides: dict[str, float | None] = Field(default_factory=dict)
    ability_overrides: dict[str, str | None] = Field(default_factory=dict)
    member_model: MonsterMemberResourceModelDTO | None = None

    @model_validator(mode="after")
    def validate_tiers(self) -> MonsterVariantDTO:
        if self.min_tier > self.max_tier:
            raise ValueError(f"Unit {self.id}: min_tier ({self.min_tier}) > max_tier ({self.max_tier})")
        return self


class FamilyHierarchyDTO(BaseModel):
    minions: list[str] = Field(default_factory=list)
    veterans: list[str] = Field(default_factory=list)
    elites: list[str] = Field(default_factory=list)
    boss: list[str] = Field(default_factory=list)


class MonsterFamilyDTO(BaseModel):
    id: str
    archetype: MonsterArchetype
    organization_type: OrganizationType
    default_tags: list[str] = Field(default_factory=list)
    hierarchy: FamilyHierarchyDTO
    combat_profile: MonsterCombatProfileDTO | None = None
    skill_kit: MonsterSkillKitDTO | None = None
    ability_map: dict[str, MonsterAbilityDefinitionDTO] = Field(default_factory=dict)
    loot_profile: MonsterLootProfileDTO | None = None
    clan_model: MonsterClanResourceModelDTO | None = None
    member_models: list[MonsterMemberResourceModelDTO] = Field(default_factory=list)
    variants: dict[str, MonsterVariantDTO]

    @model_validator(mode="after")
    def validate_hierarchy_integrity(self) -> MonsterFamilyDTO:
        all_variant_ids = set(self.variants)
        hierarchy_ids = {
            *self.hierarchy.minions,
            *self.hierarchy.veterans,
            *self.hierarchy.elites,
            *self.hierarchy.boss,
        }
        missing = hierarchy_ids - all_variant_ids
        if missing:
            raise ValueError(f"Family {self.id}: hierarchy references missing variants: {missing}")

        member_model_ids = [member_model.variant_key for member_model in self.member_models]
        duplicated_member_models = {
            variant_key for variant_key in member_model_ids if member_model_ids.count(variant_key) > 1
        }
        if duplicated_member_models:
            raise ValueError(f"Family {self.id}: duplicate member models: {sorted(duplicated_member_models)}")
        missing_member_models = set(member_model_ids) - all_variant_ids
        if missing_member_models:
            raise ValueError(f"Family {self.id}: member models reference missing variants: {missing_member_models}")

        inline_member_models = {
            variant.member_model.variant_key for variant in self.variants.values() if variant.member_model is not None
        }
        missing_inline_models = inline_member_models - all_variant_ids
        if missing_inline_models:
            raise ValueError(
                f"Family {self.id}: inline member models reference missing variants: {missing_inline_models}"
            )
        return self
