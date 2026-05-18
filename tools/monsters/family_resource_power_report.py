from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

from src.backend.features.character.runtime.combat_math_model import MODIFIER_ALIASES
from src.backend.features.character.runtime.rules.gear_score import GEAR_SCORE_WEIGHTS
from src.backend.features.monsters.resources import get_all_family_configs, get_starter_family_ids
from src.backend.features.monsters.runtime.generation_fields import (
    build_family_modifiers,
    build_member_tier,
    build_scaled_attributes,
    build_scaled_skills,
)

if TYPE_CHECKING:
    from src.backend.features.monsters.dto.resources import (
        MonsterFamilyDTO,
        MonsterMemberResourceModelDTO,
        MonsterVariantDTO,
    )

ROLE_ORDER = {"minion": 1, "veteran": 2, "elite": 3, "boss": 4}


@dataclass(frozen=True)
class VariantPowerRow:
    family_id: str
    archetype: str
    organization_type: str
    role: str
    variant_id: str
    cost: int
    context_tier: int
    member_tier: int
    min_tier: int
    max_tier: int
    attribute_points: float
    skill_points: float
    family_modifier_points: float
    resource_power: float
    strength: int
    agility: int
    endurance: int
    perception: int
    combat_skill_count: int


@dataclass(frozen=True)
class SummaryRow:
    label: str
    count: int
    avg_power: float
    min_power: float
    max_power: float
    avg_attrs: float
    avg_skills: float
    avg_family_mods: float
    avg_cost: float


def build_rows(*, families: list[str] | None = None, tier: int | None = None) -> list[VariantPowerRow]:
    configs = get_all_family_configs()
    family_ids = families or list(get_starter_family_ids())
    rows: list[VariantPowerRow] = []
    for family_id in family_ids:
        family = configs.get(family_id)
        if family is None:
            raise ValueError(f"Unknown monster family: {family_id}")
        rows.extend(_build_family_rows(family, tier=tier))
    return sorted(rows, key=lambda row: (row.family_id, row.context_tier, ROLE_ORDER.get(row.role, 9), row.variant_id))


def summarize(rows: list[VariantPowerRow], *, key: str) -> list[SummaryRow]:
    grouped: dict[str, list[VariantPowerRow]] = defaultdict(list)
    for row in rows:
        if key == "family":
            label = row.family_id
        elif key == "family_role":
            label = f"{row.family_id}/{row.role}"
        elif key == "family_tier":
            label = f"{row.family_id}/tier:{row.context_tier}"
        else:
            raise ValueError(f"Unsupported summary key: {key}")
        grouped[label].append(row)

    return [
        SummaryRow(
            label=label,
            count=len(items),
            avg_power=_avg(row.resource_power for row in items),
            min_power=round(min(row.resource_power for row in items), 2),
            max_power=round(max(row.resource_power for row in items), 2),
            avg_attrs=_avg(row.attribute_points for row in items),
            avg_skills=_avg(row.skill_points for row in items),
            avg_family_mods=_avg(row.family_modifier_points for row in items),
            avg_cost=_avg(row.cost for row in items),
        )
        for label, items in sorted(grouped.items(), key=lambda item: _summary_sort_key(item[0]))
    ]


def _build_family_rows(family: MonsterFamilyDTO, *, tier: int | None) -> list[VariantPowerRow]:
    member_models = {member.variant_key: member for member in family.member_models}
    rows: list[VariantPowerRow] = []
    for variant in family.variants.values():
        context_tiers = _context_tiers(variant, tier=tier)
        for context_tier in context_tiers:
            rows.append(
                _build_variant_row(
                    family,
                    variant,
                    context_tier=context_tier,
                    member_model=variant.member_model or member_models.get(variant.id),
                )
            )
    return rows


def _build_variant_row(
    family: MonsterFamilyDTO,
    variant: MonsterVariantDTO,
    *,
    context_tier: int,
    member_model: MonsterMemberResourceModelDTO | None,
) -> VariantPowerRow:
    member_tier = build_member_tier(context_tier, variant, member_model)
    attributes = build_scaled_attributes(variant, member_tier, member_model).model_dump(mode="json")
    skills = build_scaled_skills(family, variant, member_model).skills
    family_modifiers = build_family_modifiers(family, member_tier)

    attribute_points = float(sum(int(value or 0) for value in attributes.values()))
    skill_points = round(sum(float(value or 0.0) for value in skills.values()) * 100.0, 2)
    family_modifier_points = _family_modifier_points(family_modifiers)
    resource_power = round(attribute_points + skill_points + family_modifier_points, 2)

    return VariantPowerRow(
        family_id=family.id,
        archetype=family.archetype,
        organization_type=family.organization_type,
        role=variant.role,
        variant_id=variant.id,
        cost=variant.cost,
        context_tier=context_tier,
        member_tier=member_tier,
        min_tier=variant.min_tier,
        max_tier=variant.max_tier,
        attribute_points=attribute_points,
        skill_points=skill_points,
        family_modifier_points=family_modifier_points,
        resource_power=resource_power,
        strength=int(attributes["strength"]),
        agility=int(attributes["agility"]),
        endurance=int(attributes["endurance"]),
        perception=int(attributes["perception"]),
        combat_skill_count=len(skills),
    )


def _family_modifier_points(family_modifiers: list[dict[str, Any]]) -> float:
    total = 0.0
    for entry in family_modifiers:
        target = str(entry.get("target") or "")
        key = MODIFIER_ALIASES.get(target, target)
        weight = GEAR_SCORE_WEIGHTS.get(key)
        if weight is None:
            continue
        total += float(entry.get("effective_value") or 0.0) * weight
    return round(total, 2)


def _context_tiers(variant: MonsterVariantDTO, *, tier: int | None) -> list[int]:
    if tier is not None:
        return [tier] if variant.min_tier <= tier <= variant.max_tier else []
    return [variant.min_tier]


def _avg(values: Any) -> float:
    vals = [float(value) for value in values]
    if not vals:
        return 0.0
    return float(Decimal(sum(vals) / len(vals)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _summary_sort_key(label: str) -> tuple[str, int, int]:
    family, _, suffix = label.partition("/")
    if suffix.startswith("tier:"):
        return family, int(suffix.removeprefix("tier:")), 0
    return family, ROLE_ORDER.get(suffix, 0), 0


def _print_summary(title: str, rows: list[SummaryRow]) -> None:
    print(title)
    for row in rows:
        print(
            f"{row.label} count={row.count} avg_power={row.avg_power:.2f} min={row.min_power:.2f} "
            f"max={row.max_power:.2f} avg_attrs={row.avg_attrs:.2f} avg_skills={row.avg_skills:.2f} "
            f"avg_family_mods={row.avg_family_mods:.2f} avg_cost={row.avg_cost:.2f}"
        )


def _print_variants(rows: list[VariantPowerRow]) -> None:
    print("VARIANTS")
    for row in rows:
        print(
            f"family={row.family_id} tier={row.context_tier} role={row.role} variant={row.variant_id} "
            f"power={row.resource_power:.2f} attrs={row.attribute_points:.2f} skills={row.skill_points:.2f} "
            f"family_mods={row.family_modifier_points:.2f} cost={row.cost} "
            f"str={row.strength} agi={row.agility} end={row.endurance} per={row.perception}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate resource-level power for monster family variants.")
    parser.add_argument("--family", action="append", dest="families", help="Family id to include. Repeatable.")
    parser.add_argument("--all-families", action="store_true", help="Include all registered families, not only starters.")
    parser.add_argument("--tier", type=int, choices=range(0, 12), help="Only variants available at this context tier.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text tables.")
    parser.add_argument("--no-variants", action="store_true", help="Hide per-variant rows.")
    args = parser.parse_args()

    families = list(get_all_family_configs()) if args.all_families else args.families
    rows = build_rows(families=families, tier=args.tier)
    payload = {
        "family_summary": [asdict(row) for row in summarize(rows, key="family")],
        "family_role_summary": [asdict(row) for row in summarize(rows, key="family_role")],
        "family_tier_summary": [asdict(row) for row in summarize(rows, key="family_tier")],
        "variants": [asdict(row) for row in rows],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    _print_summary("FAMILY_SUMMARY", summarize(rows, key="family"))
    _print_summary("FAMILY_ROLE_SUMMARY", summarize(rows, key="family_role"))
    if args.tier is None:
        _print_summary("FAMILY_TIER_SUMMARY", summarize(rows, key="family_tier"))
    if not args.no_variants:
        _print_variants(rows)


if __name__ == "__main__":
    main()
