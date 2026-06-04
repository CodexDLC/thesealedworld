from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

GeneratedMonsterRole = Literal["minion", "veteran", "elite", "boss"]
GeneratedMonsterOrganizationType = Literal["solitary", "pack", "gang", "horde", "swarm"]
MonsterItemBuildMode = Literal["natural", "base"]
MonsterItemKind = Literal["weapon", "armor", "shield", "ammo", "accessory"]


class MonsterGenerationContext(BaseModel):
    zone_id: str | None = None
    biome_id: str = "wasteland"
    habitat: MonsterHabitatDTO | None = None
    tags: list[str] = Field(default_factory=list)
    tier: int = Field(ge=0, le=7)
    threat: int | None = Field(default=None, ge=0)
    difficulty: str = "mid"
    role: str | None = None
    count: int = Field(default=1, ge=1)
    context_meta: dict[str, Any] = Field(default_factory=dict)

    @property
    def habitat_biome(self) -> str:
        return self.habitat.biome if self.habitat is not None else self.biome_id

    @property
    def habitat_keys(self) -> list[str]:
        return list(self.habitat.keys) if self.habitat is not None else []


class MonsterHabitatDTO(BaseModel):
    biome: str
    keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_habitat(self) -> MonsterHabitatDTO:
        self.biome = _normalized_token(self.biome) or "wasteland"
        self.keys = sorted({_normalized_token(key) for key in self.keys if _normalized_token(key)})
        return self


class ClanPoolPolicyEntryDTO(BaseModel):
    family_id: str
    weight: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def normalize_family_id(self) -> ClanPoolPolicyEntryDTO:
        self.family_id = _normalized_token(self.family_id)
        return self


class ClanPoolPolicyDTO(BaseModel):
    primary: list[ClanPoolPolicyEntryDTO] = Field(default_factory=list)
    secondary: list[ClanPoolPolicyEntryDTO] = Field(default_factory=list)
    blocked: list[str] = Field(default_factory=list)
    policy_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def normalize_blocked(self) -> ClanPoolPolicyDTO:
        self.blocked = sorted(
            {_normalized_token(family_id) for family_id in self.blocked if _normalized_token(family_id)}
        )
        return self


class HabitatClanPoolEntryDTO(BaseModel):
    scope_type: Literal["region", "rift"]
    scope_id: str
    clan_identity_hash: str
    family_id: str
    pool_tier: Literal["primary", "secondary"]
    weight: int = Field(ge=1)
    enabled: bool = True
    habitat: MonsterHabitatDTO
    policy_version: int = Field(default=1, ge=1)


def _normalized_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


class MonsterLocationContext(BaseModel):
    loc_id: str
    zone_id: str
    biome_id: str
    tier: int = Field(ge=0, le=7)
    danger: float = Field(default=0.0, ge=0.0)
    tags: list[str] = Field(default_factory=list)
    raw_location: dict[str, Any] = Field(default_factory=dict)


class MonsterGroupMemberPreview(BaseModel):
    monster_id: str
    name: str
    description: str
    detected_ru: str = ""
    ambush_ru: str = ""
    idle_ru: str = ""
    role: str
    variant_key: str
    member_tier: int = 0
    threat_rating: int
    hp: dict[str, Any] = Field(default_factory=dict)
    image: str | None = None
    visual: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    archetype: str | None = None
    family_id: str | None = None
    organization_type: str | None = None
    gear_score: int | None = None
    vitals: dict[str, Any] = Field(default_factory=dict)
    equipment: list[dict[str, Any]] = Field(default_factory=list)
    affixes: list[dict[str, Any]] = Field(default_factory=list)


class MonsterGroupResult(BaseModel):
    group_id: str
    group_key: str | None = None
    clan_id: str
    family_id: str
    loc_id: str
    zone_id: str | None = None
    biome_id: str
    tier: int
    danger: float
    target_budget: float
    adjusted_budget: float
    total_power: int
    monster_ids: list[str]
    actor_commitments: dict[str, str] = Field(default_factory=dict)
    encounter_texts: dict[str, str] = Field(default_factory=dict)
    previews: list[MonsterGroupMemberPreview] = Field(default_factory=list)
    reused_existing_clan: bool
    context_hash: str
    unique_hash: str
    tags: list[str] = Field(default_factory=list)


class MonsterTextContentDTO(BaseModel):
    """Minimal member presentation text persisted on a generated monster row."""

    name_ru: str = ""
    short_name_ru: str = ""
    appearance_ru: str = ""
    visual_hint: str = ""


class MonsterMetaDTO(BaseModel):
    """Stable generated actor metadata that is not combat math state."""

    archetype: str
    tags: list[str] = Field(default_factory=list)
    family_id: str | None = None
    source: dict[str, Any] = Field(default_factory=dict)


class MonsterScaledAttributesDTO(BaseModel):
    """Player-shaped generated attributes for monster combat inputs."""

    strength: int = Field(ge=0)
    agility: int = Field(ge=0)
    endurance: int = Field(ge=0)
    intellect: int = Field(ge=0)
    memory: int = Field(ge=0)
    mental: int = Field(ge=0)
    perception: int = Field(ge=0)
    projection: int = Field(ge=0)
    prediction: int = Field(ge=0)


class MonsterScaledSkillsDTO(BaseModel):
    """Player catalog skill values granted to a generated monster."""

    skills: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_skill_keys(self) -> MonsterScaledSkillsDTO:
        invalid = sorted(skill_id for skill_id in self.skills if not skill_id.startswith("skill_"))
        if invalid:
            raise ValueError(f"Monster scaled skills must use player catalog skill ids: {invalid}")
        return self


class MonsterItemLayoutDTO(BaseModel):
    equipment: dict[str, str] = Field(default_factory=dict)
    belt: dict[str, str] = Field(default_factory=dict)


class MonsterItemsProjectionDTO(BaseModel):
    """Generated item projection shaped like active-character items input."""

    layout: MonsterItemLayoutDTO = Field(default_factory=MonsterItemLayoutDTO)
    by_id: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_layout_references(self) -> MonsterItemsProjectionDTO:
        referenced_ids = {*self.layout.equipment.values(), *self.layout.belt.values()}
        missing = sorted(item_id for item_id in referenced_ids if item_id not in self.by_id)
        if missing:
            raise ValueError(f"Monster items layout references missing by_id entries: {missing}")
        return self


class MonsterItemAffixPolicyDTO(BaseModel):
    allowed_affix_ids: list[str] = Field(default_factory=list)
    forced_affix_ids: list[str] = Field(default_factory=list)
    affix_count: int = Field(default=0, ge=0, le=4)
    affix_step_count: int = Field(default=1, ge=1)


class MonsterItemBuildRequestDTO(BaseModel):
    """Monster-side batch order for one compact runtime item projection."""

    owner_key: str
    family_id: str
    member_role: GeneratedMonsterRole
    member_tier: int = Field(ge=0, le=11)
    slot: str
    mode: MonsterItemBuildMode = "base"
    item_kind: MonsterItemKind | None = None
    base_id: str | None = None
    natural_key: str | None = None
    material_id: str | None = None
    item_grade: str = ""
    affix_profile: str = ""
    rarity_tier: int = Field(default=0, ge=0, le=7)
    affix_policy: MonsterItemAffixPolicyDTO
    seed: str | None = None
    source_context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_item_source(self) -> MonsterItemBuildRequestDTO:
        if self.mode == "natural" and not self.natural_key:
            raise ValueError("natural monster item requests require natural_key")
        if self.mode == "base" and not self.base_id:
            raise ValueError("base monster item requests require base_id")
        return self


class MonsterGrantedAbilitiesDTO(BaseModel):
    known_abilities: list[str] = Field(default_factory=list)
    ability_presentations: dict[str, str] = Field(default_factory=dict)


class MonsterAIProfileDTO(BaseModel):
    behavior: str = "default"
    targeting: str = "nearest"
    range: str = "melee"
    group_logic: str = "none"
    tags: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class MonsterBalanceDTO(BaseModel):
    organization_type: GeneratedMonsterOrganizationType
    organization_divisor: float = Field(gt=0.0)


class GeneratedMonsterTemplateDTO(BaseModel):
    """Actor-document source payload used while building Mongo tier snapshots."""

    schema_version: int = Field(default=1, ge=1)
    variant_key: str
    role: GeneratedMonsterRole
    member_tier: int = Field(ge=0, le=11)
    text_content: MonsterTextContentDTO = Field(default_factory=MonsterTextContentDTO)
    meta: MonsterMetaDTO
    scaled_attributes: MonsterScaledAttributesDTO
    scaled_skills: MonsterScaledSkillsDTO = Field(default_factory=MonsterScaledSkillsDTO)
    items: MonsterItemsProjectionDTO = Field(default_factory=MonsterItemsProjectionDTO)
    granted_abilities: MonsterGrantedAbilitiesDTO = Field(default_factory=MonsterGrantedAbilitiesDTO)
    ai_profile: MonsterAIProfileDTO = Field(default_factory=MonsterAIProfileDTO)
    balance: MonsterBalanceDTO


class MonsterVitalsDTO(BaseModel):
    hp: dict[str, Any] = Field(default_factory=dict)
    energy: dict[str, Any] = Field(default_factory=dict)
    stamina: dict[str, Any] = Field(default_factory=dict)
    last_update: float | None = None


@dataclass(slots=True)
class GeneratedMonster:
    id: uuid.UUID
    clan_id: uuid.UUID
    variant_id: str
    member_hash: str
    role: str
    title: str
    short_description: str
    min_tier: int
    max_tier: int
    mongo_actor_key: str
    actor_document: dict[str, Any] = field(default_factory=dict)
    active_snapshot: dict[str, Any] = field(default_factory=dict)
    metadata_: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    source_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_status: str = "active"
    archived_at: datetime | None = None
    expires_at: datetime | None = None
    schema_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    clan: GeneratedClan | None = None

    @property
    def family_id(self) -> str | None:
        return self.clan.family_id if self.clan else None


@dataclass(slots=True)
class GeneratedClan:
    id: uuid.UUID
    family_id: str
    identity_hash: str
    context_identity: dict[str, Any]
    context_hash: str
    selected_traits: list[dict[str, Any]]
    title: str
    description: str
    encounter_texts: dict[str, Any]
    generation_version: int
    resource_version: str
    metadata_: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    source_context: dict[str, Any] = field(default_factory=dict)
    lifecycle_status: str = "active"
    archived_at: datetime | None = None
    expires_at: datetime | None = None
    schema_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    members: list[GeneratedMonster] = field(default_factory=list)

    @property
    def zone_id(self) -> str | None:
        value = self.context_identity.get("zone_id")
        return str(value) if value else None

    @property
    def unique_hash(self) -> str:
        return self.identity_hash
