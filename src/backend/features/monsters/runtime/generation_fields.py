from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.backend.features.monsters.dto.generation import (
    GeneratedMonsterTemplateDTO,
    MonsterAIProfileDTO,
    MonsterBalanceDTO,
    MonsterGrantedAbilitiesDTO,
    MonsterItemsProjectionDTO,
    MonsterMetaDTO,
    MonsterScaledAttributesDTO,
    MonsterScaledSkillsDTO,
    MonsterTextContentDTO,
)
from src.backend.features.monsters.integrations.item_generation import build_member_items_projection
from src.backend.features.monsters.skill_contract import filter_monster_combat_skills

if TYPE_CHECKING:
    from src.backend.features.items.dto.instance import RuntimeItemProjectionDTO
    from src.backend.features.monsters.dto.resources import (
        MonsterFamilyDTO,
        MonsterMemberResourceModelDTO,
        MonsterVariantDTO,
    )

ROLE_TIER_OFFSETS: dict[str, int] = {
    "minion": -1,
    "veteran": 0,
    "elite": 0,
    "boss": 1,
}

ORGANIZATION_GS_DIVISORS: dict[str, float] = {
    "swarm": 4.0,
    "horde": 3.0,
    "pack": 2.5,
    "gang": 1.5,
    "solitary": 1.0,
}


def build_member_tier(
    context_tier: int,
    variant: MonsterVariantDTO,
    member_model: MonsterMemberResourceModelDTO | None = None,
) -> int:
    policy = member_model.tier_policy if member_model else "role_offset"
    explicit_offset = member_model.member_tier_offset if member_model else 0
    if policy == "fixed":
        tier = explicit_offset
    elif policy == "clan_tier":
        tier = context_tier
    else:
        tier = context_tier + explicit_offset
    return _clamp_int(tier, 0, 11)


def build_scaled_attributes(
    variant: MonsterVariantDTO,
    member_tier: int,
    member_model: MonsterMemberResourceModelDTO | None = None,
) -> MonsterScaledAttributesDTO:
    profile = member_model.attribute_profile if member_model else {}
    raw_stats = variant.base_stats.model_dump()
    mapped = {key: int(raw_stats[key]) for key in MonsterScaledAttributesDTO.model_fields}
    flat_bonus = _number_mapping(profile.get("flat_bonus"))
    tier_bonus = _number_mapping(profile.get("tier_bonus"))
    multiplier = float(profile.get("tier_multiplier", 1.0) or 1.0)
    for key, value in mapped.items():
        scaled = value + flat_bonus.get(key, 0.0) + tier_bonus.get(key, 0.0) * member_tier
        if multiplier != 1.0:
            scaled *= 1.0 + max(0, member_tier) * (multiplier - 1.0)
        mapped[key] = max(0, int(round(scaled)))
    return MonsterScaledAttributesDTO.model_validate(mapped)


def build_scaled_skills(
    family: MonsterFamilyDTO,
    variant: MonsterVariantDTO,
    member_model: MonsterMemberResourceModelDTO | None = None,
    *,
    member_tier: int,
) -> MonsterScaledSkillsDTO:
    del family
    skill_value = _skill_value_for_tier(member_tier)
    skills: dict[str, float] = {skill_key: skill_value for skill_key in _declared_skill_keys(variant, member_model)}
    return MonsterScaledSkillsDTO(skills=filter_monster_combat_skills(skills))


def build_items(
    runtime_items: list[RuntimeItemProjectionDTO] | None = None,
    *,
    owner_key: str,
) -> MonsterItemsProjectionDTO:
    if not runtime_items:
        return MonsterItemsProjectionDTO()
    return build_member_items_projection(runtime_items, owner_key=owner_key)


def build_granted_abilities(
    family: MonsterFamilyDTO,
    variant: MonsterVariantDTO,
    member_model: MonsterMemberResourceModelDTO | None = None,
) -> MonsterGrantedAbilitiesDTO:
    return MonsterGrantedAbilitiesDTO()


def build_ai_profile(
    family: MonsterFamilyDTO,
    variant: MonsterVariantDTO,
    member_model: MonsterMemberResourceModelDTO | None = None,
) -> MonsterAIProfileDTO:
    data: dict[str, Any] = {}
    if family.clan_model:
        data.update(family.clan_model.ai_defaults)
    if member_model:
        data.update(member_model.ai_profile)
    data.setdefault("behavior", variant.role)
    data.setdefault("tags", [*family.default_tags, *variant.extra_tags])
    return MonsterAIProfileDTO.model_validate(data)


def build_balance(
    family: MonsterFamilyDTO,
    variant: MonsterVariantDTO,
    member_model: MonsterMemberResourceModelDTO | None = None,
) -> MonsterBalanceDTO:
    del variant
    member_balance = member_model.balance if member_model else {}
    divisor = float(member_balance.get("organization_divisor") or _organization_gs_divisor(family.organization_type))
    return MonsterBalanceDTO(
        organization_type=family.organization_type,
        organization_divisor=divisor,
    )


def build_text_payload(
    variant: MonsterVariantDTO,
    generated_text: dict[str, Any] | None = None,
) -> MonsterTextContentDTO:
    data = _normalize_text_content(generated_text or {})
    data.setdefault("short_name_ru", variant.id)
    data.setdefault("appearance_ru", variant.narrative_hint)
    data.setdefault("name_ru", data.get("short_name_ru", variant.id))
    return MonsterTextContentDTO.model_validate(data)


def build_meta(
    family: MonsterFamilyDTO,
    variant: MonsterVariantDTO,
    *,
    source: dict[str, Any] | None = None,
) -> MonsterMetaDTO:
    return MonsterMetaDTO(
        archetype=family.archetype,
        family_id=family.id,
        tags=list(dict.fromkeys([*family.default_tags, *variant.extra_tags, variant.role])),
        source=source or {},
    )


def _organization_gs_divisor(organization_type: str) -> float:
    return float(ORGANIZATION_GS_DIVISORS.get(str(organization_type), 1.0))


def build_generated_monster_template(
    family: MonsterFamilyDTO,
    variant: MonsterVariantDTO,
    *,
    context_tier: int,
    owner_key: str,
    member_model: MonsterMemberResourceModelDTO | None = None,
    runtime_items: list[RuntimeItemProjectionDTO] | None = None,
    generated_text: dict[str, Any] | None = None,
    source: dict[str, Any] | None = None,
) -> GeneratedMonsterTemplateDTO:
    member_tier = build_member_tier(context_tier, variant, member_model)
    return GeneratedMonsterTemplateDTO(
        variant_key=variant.id,
        role=variant.role,
        member_tier=member_tier,
        text_content=build_text_payload(variant, generated_text),
        meta=build_meta(family, variant, source=source),
        scaled_attributes=build_scaled_attributes(variant, member_tier, member_model),
        scaled_skills=build_scaled_skills(family, variant, member_model, member_tier=member_tier),
        items=build_items(runtime_items, owner_key=owner_key),
        granted_abilities=build_granted_abilities(family, variant, member_model),
        ai_profile=build_ai_profile(family, variant, member_model),
        balance=build_balance(family, variant, member_model),
    )


def _number_mapping(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, float] = {}
    for key, raw in value.items():
        if raw is None:
            continue
        if isinstance(raw, bool):
            continue
        try:
            result[str(key)] = float(raw)
        except (TypeError, ValueError):
            continue
    return result


def _declared_skill_keys(
    variant: MonsterVariantDTO,
    member_model: MonsterMemberResourceModelDTO | None,
) -> list[str]:
    keys: list[str] = []
    keys.extend(str(skill) for skill in variant.skills)

    profile = member_model.skill_profile if member_model else {}
    base = profile.get("base")
    if isinstance(base, dict | list):
        keys.extend(str(skill) for skill in base)

    return list(dict.fromkeys(keys))


def _skill_value_for_tier(member_tier: int) -> float:
    safe_tier = max(0, min(7, int(member_tier)))
    return round(safe_tier / 7.0, 4)


def _normalize_text_content(value: dict[str, Any]) -> dict[str, Any]:
    data = dict(value)
    key_map = {
        "name": "name_ru",
        "short_name": "short_name_ru",
        "appearance": "appearance_ru",
        "short_description": "appearance_ru",
    }
    for source, target in key_map.items():
        if target not in data and data.get(source):
            data[target] = data[source]
    return data


def _clamp_int(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, int(value)))
