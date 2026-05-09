from __future__ import annotations

import random
from math import floor
from typing import TYPE_CHECKING

from src.backend.features.items.dto.instance import GeneratedItemDTO, ItemGenerationRequestDTO
from src.backend.features.items.resources.affix_balance import GLOBAL_AFFIX_STEPS
from src.backend.features.items.resources.affixes.catalog import AFFIX_CATALOG, BUNDLE_CATALOG
from src.backend.features.items.resources.affixes.pools import (
    AFFIX_POOLS_BY_ITEM_TYPE,
    AFFIX_POOLS_BY_SLOT,
    AFFIX_POOLS_BY_TAG,
)
from src.backend.features.items.resources.item_grade import AFFIX_CONTAINER_RULES, GRADE_BY_RARITY_TIER

if TYPE_CHECKING:
    from src.backend.features.items.resources.affixes.schemas import AffixBundleDTO, AffixCatalogEntryDTO
    from src.backend.features.items.services.catalog_service import ItemCatalogService


_PREFIX_FORMS: dict[str, tuple[str, str, str, str]] = {
    "Ржавый": ("Ржавый", "Ржавая", "Ржавое", "Ржавые"),
    "Грязный": ("Грязный", "Грязная", "Грязное", "Грязные"),
    "Латаный": ("Латаный", "Латаная", "Латаное", "Латаные"),
    "Дырявый": ("Дырявый", "Дырявая", "Дырявое", "Дырявые"),
    "Железный": ("Железный", "Железная", "Железное", "Железные"),
    "Стальной": ("Стальной", "Стальная", "Стальное", "Стальные"),
    "Деревянный": ("Деревянный", "Деревянная", "Деревянное", "Деревянные"),
    "Кожаный": ("Кожаный", "Кожаная", "Кожаное", "Кожаные"),
    "Тканый": ("Тканый", "Тканая", "Тканое", "Тканые"),
    "Кобальтовый": ("Кобальтовый", "Кобальтовая", "Кобальтовое", "Кобальтовые"),
}


class ItemFactory:
    def __init__(self, catalog: ItemCatalogService | None = None) -> None:
        if catalog is None:
            from src.backend.features.items.services.catalog_service import ItemCatalogService

        self.catalog = catalog or ItemCatalogService.load_default()

    def generate(self, request: ItemGenerationRequestDTO) -> GeneratedItemDTO:
        base = self.catalog.get_base_item(request.base_id)
        if base is None:
            raise ValueError(f"Unknown base item: {request.base_id}")

        item_grade = request.item_grade or GRADE_BY_RARITY_TIER.get(request.rarity_tier, "common")

        material = self._resolve_material(base.allowed_materials, request.material_id, request.rarity_tier)
        tier_mult = material.tier_mult if material else 1.0
        item_tier = material.tier if material else request.rarity_tier

        scaled_power = self._scale_power(base, material, tier_mult)
        scaled_durability = round(base.base_durability * tier_mult, 2)
        scaled_implicit = self._scale_implicit_bonuses(base, material, tier_mult)

        item_type = base.type or "item"
        item_tags = list(base.narrative_tags)
        if material:
            item_tags.extend(material.narrative_tags)
        affix_item_type = self._affix_item_type(item_type, base.slot, item_tags)

        container_rules = AFFIX_CONTAINER_RULES.get(item_grade, AFFIX_CONTAINER_RULES["common"])

        seed = request.origin_ref.seed if request.origin_ref and request.origin_ref.seed else None
        rng = random.Random(seed)

        filled_affixes, bundle_ids_used = self._fill_affixes(
            container_rules=container_rules,
            item_type=affix_item_type,
            slot=base.slot,
            item_tags=item_tags,
            item_tier=item_tier,
            tier_mult=tier_mult,
            forced_bundle_ids=request.affix_bundle_ids,
            rng=rng,
        )

        bundle_narrative_tags: list[str] = []
        for bid in bundle_ids_used:
            b = BUNDLE_CATALOG.get(bid)
            if b:
                bundle_narrative_tags.extend(b.tags)

        affix_narrative_tags: list[str] = []
        for af in filled_affixes:
            affix_narrative_tags.extend(af.pop("_narrative_tags", []))

        all_tags = list(
            dict.fromkeys(
                [
                    *base.narrative_tags,
                    *(material.narrative_tags if material else []),
                    *bundle_narrative_tags,
                    *affix_narrative_tags,
                ]
            )
        )

        rarity = self.catalog.get_rarity(request.rarity_tier)
        name = self._build_instance_name(
            base.name_ru,
            rarity_name=rarity.name_ru,
            material_name=material.name_ru if material else None,
            material_prefix=material.name_prefix_ru if material else None,
        )
        description = self._build_deterministic_description(
            base_description=base.narrative_description,
            base_name=base.name_ru,
            material_description=material.narrative_description if material else None,
        )

        mechanics: dict[str, object] = {
            "implicit_bonuses": scaled_implicit,
            "material": {
                "material_id": material.id if material else None,
                "tier_mult": tier_mult,
                "tags": list(material.narrative_tags) if material else [],
            },
            "affixes": filled_affixes,
            "sockets": [],
        }

        return GeneratedItemDTO(
            template_id=f"{base.id}:{material.id if material else 'none'}:{item_grade}",
            item_type=item_type,
            rarity=rarity.enum_key,
            rarity_tier=request.rarity_tier,
            name=name,
            description=description,
            base_id=base.id,
            material_id=material.id if material else None,
            affix_bundle_ids=bundle_ids_used,
            power=scaled_power,
            durability_max=scaled_durability,
            damage_spread=base.damage_spread,
            slot=base.slot,
            valid_slots=[base.slot, *base.extra_slots],
            implicit_bonuses=scaled_implicit,
            bonuses={},
            triggers=list(base.triggers),
            narrative_tags=all_tags,
            mechanics=mechanics,
            metadata={
                "source": request.source,
                "request_ai_text": request.request_ai_text,
                "damage_type": base.damage_type,
                "defense_type": base.defense_type,
                "related_skill": base.related_skill,
                "armor_class": base.armor_class,
                "item_grade": item_grade,
            },
        )

    @staticmethod
    def _scale_power(base, material, tier_mult: float) -> float:
        if base.id == "belt":
            material_tier = int(material.tier) if material else 0
            return float(max(0, int(base.base_power) * max(1, material_tier + 1)))
        return round(base.base_power * tier_mult, 2)

    @staticmethod
    def _scale_implicit_bonuses(base, material, tier_mult: float) -> dict[str, float]:
        material_tier = int(material.tier) if material else 0
        scaled: dict[str, float] = {}
        for key, value in base.implicit_bonuses.items():
            numeric = float(value)
            if base.id == "belt" and key == "quick_slot_capacity":
                scaled[key] = float(min(8, max(0, int(numeric) + material_tier)))
                continue
            scaled[key] = round(numeric * tier_mult, 4)
        return scaled

    @staticmethod
    def _affix_item_type(item_type: str, slot: str, tags: list[str]) -> str:
        if slot == "belt_accessory":
            return "belt"
        if slot == "off_hand" and "shield" in tags:
            return "shield"
        return item_type

    def _fill_affixes(
        self,
        *,
        container_rules: dict[str, object],
        item_type: str,
        slot: str,
        item_tags: list[str],
        item_tier: int,
        tier_mult: float,
        forced_bundle_ids: list[str],
        rng: random.Random,
    ) -> tuple[list[dict[str, object]], list[str]]:
        max_count = int(container_rules["max"])  # type: ignore[arg-type]
        min_count = int(container_rules["min"])  # type: ignore[arg-type]
        bundle_chance = float(container_rules["bundle_chance"])  # type: ignore[arg-type]
        allowed_bundle_sizes: list[int] = list(container_rules["bundle_sizes"])  # type: ignore[arg-type]

        if max_count == 0:
            return [], []

        filled: list[dict[str, object]] = []
        bundle_ids_used: list[str] = []
        chosen_affix_ids: set[str] = set()

        # Forced bundles from request (treated as boss/forced drops)
        for bundle_id in forced_bundle_ids:
            bundle = BUNDLE_CATALOG.get(bundle_id)
            if bundle is None:
                continue
            if not self._bundle_matches_item(bundle, item_type, item_tags, item_tier):
                continue
            added_from_bundle = False
            for affix_id in bundle.affix_ids:
                if affix_id in chosen_affix_ids or len(filled) >= max_count:
                    continue
                entry = AFFIX_CATALOG.get(affix_id)
                if entry is None or not self._affix_matches_item(entry, item_tags, item_tier):
                    continue
                rolled = self._roll_affix(entry, tier_mult, rng)
                rolled["source"] = f"bundle:{bundle_id}"
                rolled["_narrative_tags"] = list(entry.descriptive.narrative_tags)
                filled.append(rolled)
                chosen_affix_ids.add(affix_id)
                added_from_bundle = True
            if added_from_bundle and bundle_id not in bundle_ids_used:
                bundle_ids_used.append(bundle_id)

        # Bundle chance roll (only when no forced bundles)
        if not forced_bundle_ids and bundle_chance > 0 and rng.random() < bundle_chance:
            candidates = [
                b
                for b in BUNDLE_CATALOG.values()
                if b.size in allowed_bundle_sizes and self._bundle_matches_item(b, item_type, item_tags, item_tier)
            ]
            if candidates:
                bundle = rng.choice(candidates)
                for affix_id in bundle.affix_ids:
                    if affix_id in chosen_affix_ids or len(filled) >= max_count:
                        continue
                    entry = AFFIX_CATALOG.get(affix_id)
                    if entry is None or not self._affix_matches_item(entry, item_tags, item_tier):
                        continue
                    rolled = self._roll_affix(entry, tier_mult, rng)
                    rolled["source"] = f"bundle:{bundle.id}"
                    rolled["_narrative_tags"] = list(entry.descriptive.narrative_tags)
                    filled.append(rolled)
                    chosen_affix_ids.add(affix_id)
                bundle_ids_used.append(bundle.id)

        # Fill singles to reach a target between min_count and max_count
        target = rng.randint(min_count, max_count) if min_count <= max_count else max_count
        while len(filled) < target:
            pool = self._pool_for_item(item_type, slot, item_tags, item_tier, chosen_affix_ids)
            if not pool:
                break
            affix_id = rng.choice(pool)
            entry = AFFIX_CATALOG.get(affix_id)
            if entry is None:
                chosen_affix_ids.add(affix_id)
                continue
            rolled = self._roll_affix(entry, tier_mult, rng)
            rolled["source"] = f"single:{entry.group}"
            rolled["_narrative_tags"] = list(entry.descriptive.narrative_tags)
            filled.append(rolled)
            chosen_affix_ids.add(affix_id)

        return filled, bundle_ids_used

    @staticmethod
    def _roll_affix(entry: AffixCatalogEntryDTO, tier_mult: float, rng: random.Random) -> dict[str, object]:
        profile = entry.technical.roll_profile
        step_base = entry.technical.base_value * tier_mult
        lo = max(0.0, 1.0 - profile.step_spread)
        hi = 1.0 + profile.step_spread
        step_mults = [rng.uniform(lo, hi) for _ in range(GLOBAL_AFFIX_STEPS)]
        step_roll_total = sum(step_mults)
        raw_value = step_base * step_roll_total
        value = _round_value(raw_value, profile.rounding, profile.round_digits)

        max_total = GLOBAL_AFFIX_STEPS * (1.0 + profile.step_spread)
        min_total = GLOBAL_AFFIX_STEPS * max(0.0, 1.0 - profile.step_spread)
        roll_quality = (
            round(max(0.0, min(1.0, (step_roll_total - min_total) / (max_total - min_total))), 4)
            if max_total > min_total
            else 0.5
        )

        return {
            "affix_id": entry.id,
            "value": value,
            "source": "",
            "roll_quality": roll_quality,
            "roll": {"step_roll_total": round(step_roll_total, 4)},
        }

    @staticmethod
    def _pool_for_item(
        item_type: str,
        slot: str,
        item_tags: list[str],
        item_tier: int,
        already_chosen: set[str],
    ) -> list[str]:
        type_pool = set(AFFIX_POOLS_BY_ITEM_TYPE.get(item_type, []))

        slot_pool = set(AFFIX_POOLS_BY_SLOT.get(slot, []))
        if slot_pool:
            candidate = type_pool & slot_pool
            if candidate:
                type_pool = candidate

        tag_union: set[str] = set()
        for tag in item_tags:
            if tag in AFFIX_POOLS_BY_TAG:
                tag_union.update(AFFIX_POOLS_BY_TAG[tag])
        if tag_union:
            candidate = type_pool & tag_union
            if candidate:
                type_pool = candidate

        result: list[str] = []
        for affix_id in type_pool:
            if affix_id in already_chosen:
                continue
            entry = AFFIX_CATALOG.get(affix_id)
            if entry is None:
                continue
            if not ItemFactory._affix_matches_item(entry, item_tags, item_tier):
                continue
            result.append(affix_id)
        return result

    @staticmethod
    def _bundle_matches_item(
        bundle: AffixBundleDTO,
        item_type: str,
        item_tags: list[str],
        item_tier: int,
    ) -> bool:
        if item_type not in bundle.allowed_item_types:
            return False
        if bundle.min_item_tier > item_tier:
            return False
        return all(
            (entry := AFFIX_CATALOG.get(affix_id)) is not None
            and ItemFactory._affix_matches_item(entry, item_tags, item_tier)
            for affix_id in bundle.affix_ids
        )

    @staticmethod
    def _affix_matches_item(entry: AffixCatalogEntryDTO, item_tags: list[str], item_tier: int) -> bool:
        if entry.technical.min_item_tier > item_tier:
            return False
        return not entry.technical.required_item_tags or all(
            tag in item_tags for tag in entry.technical.required_item_tags
        )

    def _resolve_material(
        self,
        allowed_categories: list[str],
        material_id: str | None,
        rarity_tier: int,
    ):
        if material_id:
            material = self.catalog.get_material(material_id)
            if material is None:
                raise ValueError(f"Unknown material: {material_id}")
            if allowed_categories and material.category not in allowed_categories:
                raise ValueError(
                    f"Material {material_id!r} category {material.category!r} is not allowed for item "
                    f"categories {allowed_categories!r}"
                )
            return material
        for category in allowed_categories:
            material = self.catalog.get_material_for_tier(category, rarity_tier)
            if material is not None:
                return material
        return None

    def _build_instance_name(
        self,
        base_name: str,
        rarity_name: str,
        material_name: str | None,
        material_prefix: str | None = None,
    ) -> str:
        if material_prefix:
            return f"{self._agree_prefix(material_prefix, base_name)} {base_name.lower()}"
        if material_name:
            return f"{material_name}: {base_name}"
        return f"{rarity_name} {base_name}"

    @staticmethod
    def _agree_prefix(prefix: str, base_name: str) -> str:
        variants = _PREFIX_FORMS.get(prefix)
        if variants is None:
            return prefix
        normalized = base_name.strip().lower()
        if normalized.endswith(("и", "ы")):
            return variants[3]
        if normalized.endswith(("а", "я")):
            return variants[1]
        if normalized.endswith(("о", "е")):
            return variants[2]
        return variants[0]

    @staticmethod
    def _build_deterministic_description(
        base_description: str | None,
        base_name: str,
        material_description: str | None,
    ) -> str:
        if base_description:
            return base_description
        if material_description:
            base_lower = base_name[0].lower() + base_name[1:] if base_name else ""
            sentence = f"{material_description} {base_lower}."
            return sentence[0].upper() + sentence[1:]
        return f"{base_name}: предмет без описания."


def _round_value(value: float, rounding: str, round_digits: int) -> float:
    if rounding == "floor_int":
        return float(floor(value))
    if rounding == "round_int":
        return float(round(value))
    return round(value, round_digits)
