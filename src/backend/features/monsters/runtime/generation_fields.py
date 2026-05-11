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

ATTRIBUTE_KEY_MAP: dict[str, str] = {
    "strength": "strength",
    "agility": "agility",
    "endurance": "endurance",
    "intelligence": "intellect",
    "wisdom": "memory",
    "men": "mental",
    "perception": "perception",
    "charisma": "projection",
    "luck": "prediction",
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
        tier = context_tier + ROLE_TIER_OFFSETS.get(variant.role, 0) + explicit_offset
    return _clamp_int(tier, variant.min_tier, variant.max_tier)


def build_scaled_attributes(
    variant: MonsterVariantDTO,
    member_tier: int,
    member_model: MonsterMemberResourceModelDTO | None = None,
) -> MonsterScaledAttributesDTO:
    profile = member_model.attribute_profile if member_model else {}
    raw_stats = variant.base_stats.model_dump()
    mapped = {target: int(raw_stats[source]) for source, target in ATTRIBUTE_KEY_MAP.items()}
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
) -> MonsterScaledSkillsDTO:
    skills: dict[str, float] = {}
    if family.skill_kit:
        skills.update(family.skill_kit.base)
        skills.update(family.skill_kit.role_bonus.get(variant.role, {}))
    skills.update(_number_mapping((member_model.skill_profile if member_model else {}).get("base")))
    skills.update(_number_mapping(variant.skill_overrides))
    return MonsterScaledSkillsDTO(skills={key: value for key, value in skills.items() if value is not None})


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
    raw_ids: list[str] = []
    raw_ids.extend(variant.skills)
    raw_ids.extend(_string_list((member_model.ability_profile if member_model else {}).get("known_abilities")))
    raw_ids.extend(_string_list((member_model.ability_profile if member_model else {}).get("guaranteed")))
    raw_ids.extend(str(value) for value in variant.ability_overrides.values() if value)

    known_abilities: list[str] = []
    presentations: dict[str, str] = {}
    for ability_id in dict.fromkeys(raw_ids):
        mapped = family.ability_map.get(ability_id)
        mechanic = mapped.mechanic if mapped else ability_id
        known_abilities.append(mechanic)
        presentations[mechanic] = mapped.presentation if mapped else ability_id
    return MonsterGrantedAbilitiesDTO(known_abilities=known_abilities, ability_presentations=presentations)


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
    family_balance = family.clan_model.balance if family.clan_model else None
    member_balance = member_model.balance if member_model else {}
    divisor = float(
        member_balance.get("organization_divisor") or (family_balance.organization_divisor if family_balance else 1.0)
    )
    base_cost = int(member_balance.get("base_cost") or variant.cost)
    effective_cost = float(member_balance.get("effective_cost") or round(base_cost / divisor, 4))
    threat_rating = int(member_balance.get("threat_rating") or base_cost)
    return MonsterBalanceDTO(
        base_cost=base_cost,
        effective_cost=effective_cost,
        threat_rating=threat_rating,
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
    data.setdefault("detected_ru", variant.narrative_hint)
    data.setdefault("ambush_ru", variant.narrative_hint)
    data.setdefault("idle_ru", variant.narrative_hint)
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
        scaled_skills=build_scaled_skills(family, variant, member_model),
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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _normalize_text_content(value: dict[str, Any]) -> dict[str, Any]:
    data = dict(value)
    key_map = {
        "name": "name_ru",
        "short_name": "short_name_ru",
        "appearance": "appearance_ru",
        "detected": "detected_ru",
        "ambush": "ambush_ru",
        "idle": "idle_ru",
    }
    for source, target in key_map.items():
        if target not in data and data.get(source):
            data[target] = data[source]
    if "detected_ru" not in data and data.get("encounter"):
        data["detected_ru"] = data["encounter"]
    if "ambush_ru" not in data and data.get("encounter"):
        data["ambush_ru"] = data["encounter"]
    if "idle_ru" not in data and data.get("behavior"):
        data["idle_ru"] = data["behavior"]
    return data


def _clamp_int(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, int(value)))
