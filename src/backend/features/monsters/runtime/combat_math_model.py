from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.backend.features.character.runtime.combat_math_model import (
    COMBAT_MODIFIER_KEYS,
    MODIFIER_ALIASES,
    CharacterCombatMathModelBuilder,
)

MonsterSizeClass = Literal["small", "medium", "large", "huge"]
MonsterOrganizationType = Literal["solitary", "pack", "gang", "clan", "legion", "horde", "swarm"]


@dataclass(frozen=True)
class MonsterPipelineProfile:
    actor_kind: str
    family_id: str
    archetype: str
    role: str
    size_class: MonsterSizeClass
    organization_type: MonsterOrganizationType
    pipeline_tags: list[str]


class MonsterCombatMathModelBuilder:
    """Builds monster combat raw with a monster-specific pipeline layer."""

    SIZE_MODIFIERS: dict[MonsterSizeClass, dict[str, float | str]] = {
        "small": {
            "evasion": 0.05,
            "physical_resistance": -0.02,
            "damage_mult": "*0.9",
        },
        "medium": {},
        "large": {
            "hp": 20.0,
            "evasion": -0.03,
            "physical_resistance": 0.03,
            "damage_mult": "*1.1",
        },
        "huge": {
            "hp": 50.0,
            "evasion": -0.06,
            "physical_resistance": 0.06,
            "damage_mult": "*1.25",
        },
    }

    ROLE_SIZE_DEFAULTS: dict[str, MonsterSizeClass] = {
        "minion": "small",
        "veteran": "medium",
        "elite": "large",
        "boss": "huge",
    }

    VALID_ORGANIZATIONS: set[str] = {"solitary", "pack", "gang", "clan", "legion", "horde", "swarm"}
    VALID_SIZES: set[str] = set(SIZE_MODIFIERS)

    def __init__(self, base_builder: CharacterCombatMathModelBuilder | None = None) -> None:
        self.base_builder = base_builder or CharacterCombatMathModelBuilder()

    def build_raw(
        self,
        *,
        attributes: Any,
        items: dict[str, Any] | None = None,
        skills: dict[str, Any] | None = None,
        monster_meta: dict[str, Any] | None = None,
        balance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw = self.base_builder.build_raw(attributes=attributes, items=items or {}, skills=skills or {})
        raw["tags"] = ["monster"]

        profile = self._pipeline_profile(monster_meta or {}, balance or {})
        raw["pipeline"] = {
            "actor_kind": profile.actor_kind,
            "family_id": profile.family_id,
            "role": profile.role,
            "size_class": profile.size_class,
            "organization_type": profile.organization_type,
            "pipeline_tags": profile.pipeline_tags,
        }
        raw["rules"] = {"attribute_profile": f"monster:{profile.archetype}"}
        self._apply_profile_modifiers(raw["modifiers"], profile)
        return raw

    @classmethod
    def _pipeline_profile(cls, monster_meta: dict[str, Any], balance: dict[str, Any]) -> MonsterPipelineProfile:
        family_id = str(monster_meta.get("family_id") or "unknown")
        archetype = cls._attribute_archetype(str(monster_meta.get("archetype") or "humanoid"))
        role = str(monster_meta.get("role") or balance.get("role") or "minion")
        organization = str(monster_meta.get("organization_type") or balance.get("organization_type") or "solitary")
        if organization not in cls.VALID_ORGANIZATIONS:
            organization = "solitary"

        size_class = cls._size_class(monster_meta, role)
        pipeline_tags = [
            f"monster:organization:{organization}",
            f"monster:size:{size_class}",
        ]
        return MonsterPipelineProfile(
            actor_kind="monster",
            family_id=family_id,
            archetype=archetype,
            role=role,
            size_class=size_class,
            organization_type=organization,  # type: ignore[arg-type]
            pipeline_tags=pipeline_tags,
        )

    @staticmethod
    def _attribute_archetype(value: str) -> str:
        return "beast" if value == "beast" else "humanoid"

    @classmethod
    def _size_class(cls, monster_meta: dict[str, Any], role: str) -> MonsterSizeClass:
        explicit = str(monster_meta.get("size_class") or monster_meta.get("size") or "")
        if explicit in cls.VALID_SIZES:
            return explicit  # type: ignore[return-value]

        tags = {str(tag) for tag in monster_meta.get("tags") or []}
        for size in ("small", "medium", "large", "huge"):
            if size in tags:
                return size  # type: ignore[return-value]
        return cls.ROLE_SIZE_DEFAULTS.get(role, "medium")

    @classmethod
    def _apply_profile_modifiers(cls, modifiers: dict[str, Any], profile: MonsterPipelineProfile) -> None:
        cls._apply_modifier_group(
            modifiers, f"monster_size:{profile.size_class}", cls.SIZE_MODIFIERS[profile.size_class]
        )

    @staticmethod
    def _apply_modifier_group(modifiers: dict[str, Any], source: str, values: dict[str, float | str]) -> None:
        for target, value in values.items():
            key = MODIFIER_ALIASES.get(target, target)
            if key not in COMBAT_MODIFIER_KEYS:
                continue
            modifiers.setdefault(key, {"base": 0.0, "source": {}, "temp": {}})
            modifiers[key]["source"][source] = value if isinstance(value, str) else round(float(value), 4)


__all__ = ["MonsterCombatMathModelBuilder", "MonsterPipelineProfile"]
