from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from src.backend.features.character.runtime.combat_math_model import COMBAT_MODIFIER_KEYS, MODIFIER_ALIASES

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.backend.features.monsters.dto.resources import MonsterFamilyDTO

MONSTER_CLAN_TRAIT_CATALOG_VERSION = 1
MONSTER_CLAN_TRAITS_MAX = 2


class MonsterClanTraitModifierDTO(BaseModel):
    target: str
    base: float = 0.0
    per_tier: float = 0.0

    @property
    def normalized_target(self) -> str:
        return MODIFIER_ALIASES.get(self.target, self.target) if self.target in _VALID_MODIFIER_TARGETS else ""

    @model_validator(mode="after")
    def validate_target(self) -> MonsterClanTraitModifierDTO:
        if self.target not in _VALID_MODIFIER_TARGETS:
            raise ValueError(f"Unknown monster clan trait modifier target: {self.target}")
        return self


class MonsterClanTraitDTO(BaseModel):
    key: str
    label: str
    tags: list[str] = Field(default_factory=list)
    association_tags: list[str] = Field(default_factory=list)
    allowed_biome_tags: list[str] = Field(default_factory=list)
    denied_biome_tags: list[str] = Field(default_factory=list)
    allowed_archetypes: list[str] = Field(default_factory=list)
    denied_archetypes: list[str] = Field(default_factory=list)
    allowed_family_tags: list[str] = Field(default_factory=list)
    denied_family_tags: list[str] = Field(default_factory=list)
    allowed_family_ids: list[str] = Field(default_factory=list)
    denied_family_ids: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    weight: int = Field(default=10, gt=0)
    modifiers: list[MonsterClanTraitModifierDTO] = Field(default_factory=list)
    flavor: str = ""

    @model_validator(mode="after")
    def validate_trait(self) -> MonsterClanTraitDTO:
        if self.key in set(self.conflicts):
            raise ValueError(f"Monster clan trait conflicts with itself: {self.key}")
        if not self.modifiers:
            raise ValueError(f"Monster clan trait has no modifiers: {self.key}")
        return self


_VALID_MODIFIER_TARGETS = set(COMBAT_MODIFIER_KEYS) | set(MODIFIER_ALIASES)


_TRAITS_RAW: list[dict[str, object]] = [
    {
        "key": "fortified_scavengers",
        "label": "Fortified scavengers",
        "tags": ["fortified", "cover", "scavenger"],
        "association_tags": ["city_ruins", "outer_wall", "guard_ruins", "bastion", "barricades", "camp_guard"],
        "allowed_archetypes": ["humanoid"],
        "denied_family_tags": ["beast"],
        "weight": 18,
        "conflicts": ["camouflaged_stalkers"],
        "modifiers": [
            {"target": "armor", "base": 2.0, "per_tier": 1.0},
            {"target": "physical_resistance", "base": 0.02, "per_tier": 0.01},
        ],
        "flavor": "Uses barricades, scavenged plates, and ruined walls as part of its fighting style.",
    },
    {
        "key": "ambush_drilled",
        "label": "Ambush drilled",
        "tags": ["ambush", "discipline"],
        "association_tags": ["city_ruins", "guard_ruins", "outer_wall", "roadside_camp", "bandit_gang"],
        "allowed_archetypes": ["humanoid", "beast"],
        "weight": 14,
        "modifiers": [
            {"target": "anti_dodge_chance", "base": 0.02, "per_tier": 0.005},
            {"target": "main_hand_accuracy", "base": 0.01, "per_tier": 0.005},
        ],
        "flavor": "Fights from prepared angles and punishes movement through narrow ground.",
    },
    {
        "key": "scrap_tinkerers",
        "label": "Scrap tinkerers",
        "tags": ["scrap", "tinkerer", "unstable"],
        "association_tags": ["goblin", "goblin_tribe", "scrap", "collapsed_workshop", "unstable"],
        "allowed_family_ids": ["goblin_tribe"],
        "weight": 18,
        "modifiers": [
            {"target": "item_accuracy", "base": 0.02, "per_tier": 0.005},
            {"target": "armor_penetration_pct", "base": 0.01, "per_tier": 0.005},
        ],
        "flavor": "Improvised tools and traps make their attacks awkward but hard to fully read.",
    },
    {
        "key": "plague_borne",
        "label": "Plague borne",
        "tags": ["plague", "disease", "rot"],
        "association_tags": ["sewer", "rot", "disease", "undercity_seep", "rat", "rat_swarm"],
        "denied_archetypes": ["construct"],
        "weight": 20,
        "conflicts": ["ember_blooded"],
        "modifiers": [
            {"target": "nature_resistance", "base": 0.03, "per_tier": 0.01},
            {"target": "dark_resistance", "base": 0.02, "per_tier": 0.005},
        ],
        "flavor": "Carries sickness as pressure and survives in corrupted ground.",
    },
    {
        "key": "rot_adapted",
        "label": "Rot adapted",
        "tags": ["rot", "endurance"],
        "association_tags": ["sewer", "rot", "disease", "swamp", "rat_swarm"],
        "denied_archetypes": ["construct"],
        "weight": 12,
        "conflicts": ["ash_hardened"],
        "modifiers": [
            {"target": "physical_resistance", "base": 0.015, "per_tier": 0.005},
            {"target": "hp", "base": 4.0, "per_tier": 2.0},
        ],
        "flavor": "Bodies are hardened by filth, damp, and old infection.",
    },
    {
        "key": "swarm_pressure",
        "label": "Swarm pressure",
        "tags": ["swarm", "pressure"],
        "association_tags": ["swarm", "rat_swarm", "horde", "goblin_tribe"],
        "weight": 14,
        "modifiers": [
            {"target": "anti_dodge_chance", "base": 0.025, "per_tier": 0.005},
            {"target": "counter_attack_chance", "base": 0.01, "per_tier": 0.005},
        ],
        "flavor": "Wins ground by crowding, biting, and forcing mistakes.",
    },
    {
        "key": "ash_hardened",
        "label": "Ash hardened",
        "tags": ["ash", "heat", "fire"],
        "association_tags": ["lava", "fire", "ash", "heat", "falling_ash", "scorched_grass"],
        "denied_family_ids": ["rat_swarm", "wolf_pack"],
        "weight": 16,
        "conflicts": ["rot_adapted", "plague_borne"],
        "modifiers": [
            {"target": "fire_resistance", "base": 0.05, "per_tier": 0.015},
            {"target": "armor", "base": 1.0, "per_tier": 0.5},
        ],
        "flavor": "Heat and ash have toughened skin, armor, and instincts.",
    },
    {
        "key": "ember_blooded",
        "label": "Ember blooded",
        "tags": ["fire", "aggression"],
        "association_tags": ["lava", "fire", "heat", "magma_ocean"],
        "denied_family_ids": ["rat_swarm"],
        "weight": 10,
        "conflicts": ["plague_borne"],
        "modifiers": [
            {"target": "fire_resistance", "base": 0.04, "per_tier": 0.01},
            {"target": "main_hand_crit_chance", "base": 0.01, "per_tier": 0.005},
        ],
        "flavor": "Fights hot, reckless, and hard to burn out.",
    },
    {
        "key": "camouflaged_stalkers",
        "label": "Camouflaged stalkers",
        "tags": ["camouflage", "forest", "ambush"],
        "association_tags": ["forest", "overgrowth", "overgrown_kennel", "accelerated_growth", "giant_roots"],
        "denied_family_ids": ["bandit_gang"],
        "weight": 16,
        "conflicts": ["fortified_scavengers"],
        "modifiers": [
            {"target": "evasion", "base": 0.04, "per_tier": 0.01},
            {"target": "anti_dodge_chance", "base": 0.01, "per_tier": 0.005},
        ],
        "flavor": "Breaks silhouettes against roots, brush, and ruined green cover.",
    },
    {
        "key": "predator_stalkers",
        "label": "Predator stalkers",
        "tags": ["predator", "flank", "forest"],
        "association_tags": ["wolf", "wolf_pack", "predator", "forest", "overgrowth"],
        "allowed_family_ids": ["wolf_pack"],
        "weight": 20,
        "modifiers": [
            {"target": "main_hand_crit_chance", "base": 0.015, "per_tier": 0.005},
            {"target": "evasion", "base": 0.02, "per_tier": 0.005},
        ],
        "flavor": "Tracks openings as a pack and attacks when prey turns wrong.",
    },
    {
        "key": "void_touched",
        "label": "Void touched",
        "tags": ["void", "rift"],
        "association_tags": ["rift", "void", "void_rifts", "rift_scavenger_beasts", "tier_1_rift"],
        "weight": 16,
        "conflicts": ["gravity_warped"],
        "modifiers": [
            {"target": "dark_resistance", "base": 0.04, "per_tier": 0.01},
            {"target": "magic_resist", "base": 0.02, "per_tier": 0.005},
        ],
        "flavor": "Carries pressure from the rift and resists hostile magic unevenly.",
    },
    {
        "key": "gravity_warped",
        "label": "Gravity warped",
        "tags": ["gravity", "unstable", "rift"],
        "association_tags": ["gravity", "unstable", "low_gravity", "inverted_gravity", "floating_pebbles"],
        "weight": 12,
        "conflicts": ["void_touched"],
        "modifiers": [
            {"target": "evasion", "base": 0.03, "per_tier": 0.005},
            {"target": "accuracy", "base": -0.01, "per_tier": 0.0},
        ],
        "flavor": "Movement and strikes bend around unreliable weight and falling angles.",
    },
]

_CATALOG: tuple[MonsterClanTraitDTO, ...] = tuple(MonsterClanTraitDTO.model_validate(item) for item in _TRAITS_RAW)
_CATALOG_BY_KEY = {trait.key: trait for trait in _CATALOG}
for _trait in _CATALOG:
    unknown_conflicts = set(_trait.conflicts) - set(_CATALOG_BY_KEY)
    if unknown_conflicts:
        raise ValueError(f"Monster clan trait {_trait.key} references unknown conflicts: {sorted(unknown_conflicts)}")


def get_monster_clan_trait_catalog() -> tuple[MonsterClanTraitDTO, ...]:
    return _CATALOG


def get_monster_clan_trait(key: str) -> MonsterClanTraitDTO | None:
    return _CATALOG_BY_KEY.get(key)


def select_monster_clan_traits(
    family: MonsterFamilyDTO,
    *,
    biome_id: str,
    context_tags: Sequence[str],
    seed: str,
    max_traits: int = MONSTER_CLAN_TRAITS_MAX,
) -> list[MonsterClanTraitDTO]:
    del seed
    return select_monster_clan_traits_for_habitat(
        family,
        biome_id=biome_id,
        habitat_keys=context_tags,
        max_traits=max_traits,
    )


def select_monster_clan_traits_for_habitat(
    family: MonsterFamilyDTO,
    *,
    biome_id: str,
    habitat_keys: Sequence[str],
    max_traits: int = MONSTER_CLAN_TRAITS_MAX,
) -> list[MonsterClanTraitDTO]:
    if max_traits <= 0:
        return []
    candidates = [
        trait
        for trait in _CATALOG
        if _trait_applies(trait, family=family, biome_id=biome_id, context_tags=habitat_keys)
    ]
    ordered = sorted(candidates, key=lambda trait: (-trait.weight, trait.key))
    selected: list[MonsterClanTraitDTO] = []
    blocked: set[str] = set()
    for trait in ordered:
        if len(selected) >= max_traits:
            break
        if trait.key in blocked:
            continue
        selected.append(trait)
        blocked.update(trait.conflicts)
        blocked.update(existing.key for existing in _CATALOG if trait.key in set(existing.conflicts))
    return selected


def serialize_selected_trait(trait: MonsterClanTraitDTO) -> dict[str, object]:
    return {
        "key": trait.key,
        "label": trait.label,
        "tags": list(trait.tags),
        "flavor": trait.flavor,
        "modifiers": [modifier.model_dump(mode="json") for modifier in trait.modifiers],
    }


def _trait_applies(
    trait: MonsterClanTraitDTO,
    *,
    family: MonsterFamilyDTO,
    biome_id: str,
    context_tags: Sequence[str],
) -> bool:
    context = {str(biome_id), *map(str, context_tags)}
    family_tags = {family.id, family.archetype, *map(str, family.default_tags)}
    all_tags = context | family_tags
    if trait.association_tags and not (set(trait.association_tags) & all_tags):
        return False
    if trait.allowed_biome_tags and not (set(trait.allowed_biome_tags) & context):
        return False
    if set(trait.denied_biome_tags) & context:
        return False
    if trait.allowed_archetypes and family.archetype not in set(trait.allowed_archetypes):
        return False
    if family.archetype in set(trait.denied_archetypes):
        return False
    if trait.allowed_family_ids and family.id not in set(trait.allowed_family_ids):
        return False
    if family.id in set(trait.denied_family_ids):
        return False
    if trait.allowed_family_tags and not (set(trait.allowed_family_tags) & family_tags):
        return False
    return not set(trait.denied_family_tags) & family_tags


def _weighted_score(seed: str, trait: MonsterClanTraitDTO) -> float:
    digest = hashlib.md5(f"{seed}:{trait.key}".encode(), usedforsecurity=False).hexdigest()
    raw = int(digest[:12], 16)
    return raw / float(trait.weight)


__all__ = [
    "MONSTER_CLAN_TRAIT_CATALOG_VERSION",
    "MONSTER_CLAN_TRAITS_MAX",
    "MonsterClanTraitDTO",
    "MonsterClanTraitModifierDTO",
    "get_monster_clan_trait",
    "get_monster_clan_trait_catalog",
    "select_monster_clan_traits",
    "serialize_selected_trait",
]
